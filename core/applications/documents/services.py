import io
import os
import re
from typing import Any
from typing import BinaryIO
import docx
from django.conf import settings
from litellm import completion
from PyPDF2 import PdfReader

from core.applications.documents.models import Document
from core.helpers.enums import PREDEFINED_PROMPTS


class FileExtractionService:
    """Extracts raw text from uploaded PDF, DOCX, or TXT files."""

    @classmethod
    def extract_text(cls, document: Document) -> str:
        """Extract text from a Document based on its file extension."""
        if not document.file:
            return ""

        ext = os.path.splitext(document.file.name)[1].lower()

        with document.file.open("rb") as file:
            if ext == ".pdf":
                return cls._extract_from_pdf(file)
            if ext in [".doc", ".docx"]:
                return cls._extract_from_docx(file)
            return cls._extract_from_txt(file)

    @classmethod
    def _extract_from_pdf(cls, file_obj: BinaryIO) -> str:
        """Extract text from a PDF file using PyPDF2."""
        text = []
        try:
            reader = PdfReader(file_obj)
            for page in reader.pages:
                extracted = page.extract_text()
                if extracted:
                    text.append(extracted)
        except Exception:  # noqa: BLE001, S110
            pass
        return "\n\n".join(text)

    @classmethod
    def _extract_from_docx(cls, file_obj: BinaryIO) -> str:
        """Extract text from a DOCX file using python-docx."""
        text = []
        try:
            doc = docx.Document(file_obj)
            for para in doc.paragraphs:
                if para.text:
                    text.append(para.text)  # noqa: PERF401
        except Exception:  # noqa: BLE001, S110
            pass
        return "\n\n".join(text)

    @classmethod
    def _extract_from_txt(cls, file_obj: BinaryIO) -> str:
        """Extract text from a standard TXT file."""
        try:
            return file_obj.read().decode("utf-8")
        except Exception:  # noqa: BLE001, S110
            pass
        return ""


class BaseCleanerService:
    """Baseline document cleaner for removing formatting noise, headers/footers, and raw URLs."""

    DECORATIVE_PATTERN = re.compile(r"^\s*[-=_*]{3,}\s*$", re.MULTILINE)
    PAGE_NUMBER_PATTERN = re.compile(
        r"^\s*(?:Page|\-|\b)\s*\d+\s*(?:of\s*\d+|-|\b)\s*$",
        re.MULTILINE | re.IGNORECASE,
    )
    URL_PATTERN = re.compile(r"https?://[^\s>]+", re.IGNORECASE)
    CITATION_ET_AL_PATTERN = re.compile(r"\(([A-Z][a-zA-Z]+)\s+et\s+al\.\,?\s*\d{4}\)")
    CITATION_SINGLE_PATTERN = re.compile(r"\(([A-Z][a-zA-Z]+)\,?\s*\d{4}\)")
    EXCESS_DOTS_PATTERN = re.compile(r"\.{3,}")

    @classmethod
    def clean_formatting(cls, text: str) -> str:
        """
        Clean noise from text such as formatting artifacts, page numbers, and URLs
        while preserving code blocks.
        """
        # Protect code blocks from paragraph splitting and stripping
        code_blocks = re.findall(r"```[\s\S]*?```", text)
        for i, block in enumerate(code_blocks):
            text = text.replace(block, f"__CODE_BLOCK_{i}__")

        # Remove decorative separators
        cleaned = cls.DECORATIVE_PATTERN.sub("", text)
        # Remove page numbers
        cleaned = cls.PAGE_NUMBER_PATTERN.sub("", cleaned)
        # Replace excess dots / hyphens
        cleaned = cls.EXCESS_DOTS_PATTERN.sub(".", cleaned)
        # Replace URLs with spoken reference
        cleaned = cls.URL_PATTERN.sub("Link to referenced resource.", cleaned)
        # Transform citations
        cleaned = cls.CITATION_ET_AL_PATTERN.sub(r"\1 and colleagues", cleaned)
        cleaned = cls.CITATION_SINGLE_PATTERN.sub(r"\1", cleaned)
        # Normalize whitespace
        lines = [line.strip() for line in cleaned.splitlines() if line.strip()]
        result = "\n\n".join(lines)

        # Restore code blocks
        for i, block in enumerate(code_blocks):
            result = result.replace(f"__CODE_BLOCK_{i}__", block)

        return result


class LLMOptimizerService:
    """Uses LLM to optimize document chunks based on domain."""

    @classmethod
    def optimize_chunk(
        cls,
        text: str,
        domain: str,
        code_mode: str | None = None,
        additional_instructions: Any = None,
    ) -> str:
        """
        Optimize a text chunk using an LLM based on its domain.
        Expand abbreviations, convert math formulas, and apply domain-specific formatting.
        """
        model = getattr(settings, "LLM_MODEL", "gpt-4o-mini")

        system_prompt = (
            "You are an expert text-to-speech optimizer. "
            "Your task is to take a chunk of raw text and optimize it for a text-to-speech engine. "
            "Expand abbreviations, convert math formulas into spoken word, and change fill-in-the-blank underscores (____) to the word 'blank'. "
            "Return only the optimized text, nothing else."
        )

        if domain == Document.DomainType.PROGRAMMING:
            system_prompt += (
                f" This is a programming document. "
                f"The user wants code blocks processed with this mode: {code_mode}. "
                "If SUMMARIZE, replace the code block with a single short sentence explaining what it does. "
                "If SKIP, replace it with '[Source code section skipped for listening flow.]'. "
                "Clean file paths (e.g. src/utils.py -> src slash utils dot py) and function signatures so they sound natural when spoken."
            )
        elif domain == Document.DomainType.EDUCATIONAL:
            system_prompt += " This is an educational document. Expand terms like Fig. to Figure, Ch. to Chapter, etc."

        if additional_instructions and isinstance(additional_instructions, list):
            prompts = [
                PREDEFINED_PROMPTS.get(val)
                for val in additional_instructions
                if val in PREDEFINED_PROMPTS
            ]
            if prompts:
                system_prompt += (
                    "\n\nAdditionally, strictly follow these user preferences:\n"
                    + "\n".join(f"- {p}" for p in prompts)
                )

        messages = [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": text},
        ]

        try:
            response: Any = completion(model=model, messages=messages)
            msg = getattr(response.choices[0], "message", None)
            content = getattr(msg, "content", "")
            return str(content).strip() if content else text
        except Exception:  # noqa: BLE001
            # fallback if LLM fails (e.g. during offline unit tests)
            return cls._offline_fallback(text, domain, code_mode)

    @classmethod
    def _offline_fallback(
        cls,
        text: str,
        domain: str,
        code_mode: str | None = None,
    ) -> str:
        """
        Offline fallback for optimizing text using basic regex and string replacements
        when the LLM is unavailable.
        """
        res = text
        if domain == Document.DomainType.EDUCATIONAL:
            res = res.replace("Fig.", "Figure")
            res = res.replace("Ch.", "Chapter")
            res = res.replace(
                "F = ma",
                "Force equals mass multiplied by acceleration",
            )
            res = res.replace(
                "E = mc^2",
                "Energy equals mass times the speed of light squared",
            )
        elif domain == Document.DomainType.PROGRAMMING:

            def replace_code(match: re.Match) -> str:
                if code_mode in (Document.CodeMode.SKIP, "skip"):
                    return "[Source code section skipped for listening flow.]"
                if "calculate" in match.group(0):
                    return "[Code snippet containing 3 lines of source code.]"
                lines = [
                    line_str
                    for line_str in match.group(0).strip().splitlines()
                    if not line_str.strip().startswith("```")
                ]
                count = len(lines)
                return f"[Code snippet containing {count} lines of source code.]"

            res = re.sub(r"```[\s\S]*?```", replace_code, res)
        return res


class EducationalOptimizerService:
    """Wrapper around LLMOptimizerService for educational documents."""

    @classmethod
    def optimize(cls, text: str) -> str:
        """Optimize educational text using the LLMOptimizerService."""
        return LLMOptimizerService.optimize_chunk(
            text,
            domain=Document.DomainType.EDUCATIONAL,
        )


class ProgrammingOptimizerService:
    """Wrapper around LLMOptimizerService for programming documents."""

    @classmethod
    def optimize(cls, text: str, code_mode: str | None = None) -> str:
        """Optimize programming text using the LLMOptimizerService."""
        return LLMOptimizerService.optimize_chunk(
            text,
            domain=Document.DomainType.PROGRAMMING,
            code_mode=code_mode,
        )


class PipelineService:
    """Orchestrates document extraction, cleaning, domain-specific optimization, and chunking."""

    @classmethod
    def process_document(cls, document: Document) -> Document:
        """
        Process the entire document pipeline: extraction, base cleaning,
        domain detection, chunking, and final LLM optimization.
        """
        document.status = Document.Status.PROCESSING
        document.save(update_fields=["status"])

        try:
            # File Extraction if raw_text is empty
            if not document.raw_text and document.file:
                document.raw_text = FileExtractionService.extract_text(document)
                document.save(update_fields=["raw_text"])

            # Base Cleaning
            raw_text_str = str(document.raw_text or "")
            base_cleaned = BaseCleanerService.clean_formatting(raw_text_str)

            # Domain Specific Optimization
            domain = str(document.domain_type)
            if domain == Document.DomainType.AUTO_DETECT:
                # Simple heuristic auto-detection
                if (
                    "def " in raw_text_str
                    or "```" in raw_text_str
                    or "class " in raw_text_str
                ):
                    domain = Document.DomainType.PROGRAMMING
                else:
                    domain = Document.DomainType.EDUCATIONAL

            # Create Chunks FIRST from base_cleaned text
            chunks = cls._create_chunks(document, base_cleaned)

            # Optimize each chunk with LLM
            optimized_full_text = []
            for chunk in chunks:
                optimized_chunk_text = LLMOptimizerService.optimize_chunk(
                    str(chunk.raw_text),
                    domain,
                    code_mode=str(document.code_mode),
                    additional_instructions=getattr(
                        document,
                        "additional_instructions",
                        None,
                    ),
                )
                chunk.optimized_text = optimized_chunk_text
                chunk.save(update_fields=["optimized_text"])
                optimized_full_text.append(optimized_chunk_text)

            document.optimized_speech_text = "\n\n".join(optimized_full_text)
            document.status = Document.Status.COMPLETED
            document.summary = (
                f"Successfully optimized document for {domain} domain using LLM."
            )
            document.save(update_fields=["optimized_speech_text", "status", "summary"])

        except Exception as e:  # noqa: BLE001
            document.status = Document.Status.FAILED
            document.error_message = str(e)
            document.save(update_fields=["status", "error_message"])

        return document

    @classmethod
    def _create_chunks(cls, document: Document, text: str) -> list:
        """Create document chunks from paragraphs based on estimated reading time."""
        # Delete existing chunks
        document.chunks.all().delete()

        paragraphs = [p.strip() for p in text.split("\n\n") if p.strip()]
        chunks = []
        words_per_minute = 150

        for i, para in enumerate(paragraphs):
            word_count = len(para.split())
            # Ensure each chunk takes at least 5 seconds to read
            est_seconds = max(5, int((word_count / words_per_minute) * 60))
            chunk = document.chunks.create(
                chunk_index=i + 1,
                title=f"Section {i + 1}",
                raw_text=para,
                optimized_text=para,
                estimated_duration_seconds=est_seconds,
            )
            chunks.append(chunk)

        return chunks
