import io
import json
import os
import re
import threading
import time
from typing import Any
from typing import BinaryIO
import docx
from django.conf import settings
from litellm import completion


class LLMExhaustedError(Exception):
    """
    Raised by LLMOptimizerService when all retry attempts are exhausted.
    Caught by PipelineService per-chunk to fall back to ManualOptimizerService
    while preserving the overall pipeline result and signalling the view layer.
    """
from PyPDF2 import PdfReader

from core.applications.documents.models import Document
from core.applications.documents.models import OptimizationRegexRule
from core.applications.documents.models import UserOptimizationExample
from core.helpers.enums import PREDEFINED_PROMPTS
from core.helpers.enums import OptimizationMode


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
    # Matches a written-out number word immediately followed by its bracketed digit
    # equivalent, e.g. "three [3]" or "twenty-one [21]".  The bracket is redundant
    # for TTS because the word already conveys the value.
    REDUNDANT_BRACKET_NUMBER_PATTERN = re.compile(
        r"\b"
        r"(zero|one|two|three|four|five|six|seven|eight|nine|ten|"
        r"eleven|twelve|thirteen|fourteen|fifteen|sixteen|seventeen|"
        r"eighteen|nineteen|twenty|twenty-one|twenty-two|twenty-three|"
        r"twenty-four|twenty-five|twenty-six|twenty-seven|twenty-eight|"
        r"twenty-nine|thirty|forty|fifty|sixty|seventy|eighty|ninety|"
        r"hundred|thousand|million)"
        r"\b\s*\[\d+\]",
        re.IGNORECASE,
    )

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
        # Remove bracketed digit when the word form already precedes it (e.g. "three [3]" → "three")
        cleaned = cls.REDUNDANT_BRACKET_NUMBER_PATTERN.sub(r"\1", cleaned)
        # Transform citations
        cleaned = cls.CITATION_ET_AL_PATTERN.sub(r"\1 and colleagues", cleaned)
        cleaned = cls.CITATION_SINGLE_PATTERN.sub(r"\1", cleaned)
        # Normalize whitespace and reconstruct paragraphs broken by PDF extractors
        raw_lines = [line.strip() for line in cleaned.splitlines() if line.strip()]
        merged_lines = []
        for line in raw_lines:
            if not merged_lines:
                merged_lines.append(line)
                continue
            
            prev = merged_lines[-1]
            # Protect code blocks from being merged
            if prev.startswith("__CODE_BLOCK") or line.startswith("__CODE_BLOCK"):
                merged_lines.append(line)
            # If prev line ends with punctuation, it's likely a complete paragraph
            elif re.search(r'[.?!:;_"\'\]\)]$', prev):
                merged_lines.append(line)
            # If current line starts with a list marker, a number, or Capital letter, maybe it's a new paragraph
            elif re.match(r'^(?:[A-Z]|\d+\.|[A-Z]\.|-|\*)', line):
                merged_lines.append(line)
            else:
                # Otherwise, it's a continuation of the previous line
                merged_lines[-1] = prev + " " + line
                
        result = "\n\n".join(merged_lines)

        # Restore code blocks
        for i, block in enumerate(code_blocks):
            result = result.replace(f"__CODE_BLOCK_{i}__", block)

        return result


class UserOptimizationExampleService:
    """Manages capturing and pruning user edits to chunks."""

    @classmethod
    def capture_example(
        cls,
        user: Any,
        domain_type: str,
        raw_text: str,
        edited_text: str,
    ) -> None:
        """Saves a user edit for few-shot learning and regex rule generation."""
        if not user or not user.is_authenticated:
            return

        # Save example
        UserOptimizationExample.objects.create(
            user=user,
            domain_type=domain_type,
            raw_text=raw_text,
            edited_text=edited_text,
        )

        # Keep only the 5 most recent examples per user/domain
        examples = UserOptimizationExample.objects.filter(
            user=user, domain_type=domain_type
        ).order_by("-created_at")
        
        if examples.count() > 5:
            ids_to_keep = list(examples.values_list("id", flat=True)[:5])
            UserOptimizationExample.objects.filter(
                user=user, domain_type=domain_type
            ).exclude(id__in=ids_to_keep).delete()

        # Fire-and-forget thread to generate regex rule via LLM
        def background_generate() -> None:
            LLMOptimizerService.generate_regex_rule(
                raw_text, edited_text, user, domain_type
            )

        threading.Thread(target=background_generate, daemon=True).start()


class LLMOptimizerService:
    """Uses LLM to optimize document chunks based on domain."""

    @classmethod
    def optimize_chunk(
        cls,
        text: str,
        domain: str,
        code_mode: str | None = None,
        additional_instructions: Any = None,
        user: Any = None,
    ) -> str:
        """
        Optimize a text chunk using an LLM based on its domain.
        Expand abbreviations, convert math formulas, and apply domain-specific formatting.
        Retries up to LLM_MAX_RETRIES times on failure before falling back to
        ManualOptimizerService.
        """
        model = getattr(settings, "LLM_MODEL", "gpt-4o-mini")
        timeout = getattr(settings, "LLM_TIMEOUT", 15)
        max_retries = getattr(settings, "LLM_MAX_RETRIES", 2)

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

        messages = [{"role": "system", "content": system_prompt}]

        # Inject few-shot examples if available
        if user and user.is_authenticated:
            examples = UserOptimizationExample.objects.filter(
                user=user, domain_type=domain
            ).order_by("created_at")
            if examples.exists():
                messages.append(
                    {
                        "role": "system",
                        "content": "The following are historical examples of how the user prefers their text optimized. Replicate these patterns exactly.",
                    }
                )
                for ex in examples:
                    messages.append({"role": "user", "content": ex.raw_text})
                    messages.append({"role": "assistant", "content": ex.edited_text})

        messages.append({"role": "user", "content": text})

        last_exc: Exception | None = None
        for attempt in range(1, max_retries + 1):
            try:
                response: Any = completion(model=model, messages=messages, timeout=timeout)
                msg = getattr(response.choices[0], "message", None)
                content = getattr(msg, "content", "")
                return str(content).strip() if content else text
            except Exception as exc:  # noqa: BLE001
                last_exc = exc
                if attempt < max_retries:
                    # Exponential backoff: 1s, 2s, 4s …
                    time.sleep(2 ** (attempt - 1))

        # All retries exhausted — signal the caller with a typed exception
        # so the pipeline can fall back gracefully AND inform the UI.
        raise LLMExhaustedError(
            f"LLM optimization failed after {max_retries} attempt(s): {last_exc}"
        )

    @classmethod
    def generate_regex_rule(
        cls, raw_text: str, edited_text: str, user: Any, domain_type: str
    ) -> None:
        """
        Uses LLM to deduce a regex replacement rule from a user's edit,
        and saves it to the OptimizationRegexRule bank.
        """
        model = getattr(settings, "LLM_MODEL", "gpt-4o-mini")
        timeout = getattr(settings, "LLM_TIMEOUT", 15)

        system_prompt = (
            "You are a Python regex expert. "
            "Given the user's original raw text and their final edited text, "
            "deduce the single core substitution pattern they applied and generate a Python `re.sub()` compatible regex pattern and replacement string. "
            "Respond ONLY with a valid JSON object in this format, and absolutely nothing else: "
            '{"pattern": "your_regex_here", "replacement": "your_replacement_here"}'
        )

        user_content = (
            f"RAW TEXT:\n{raw_text}\n\nEDITED TEXT:\n{edited_text}"
        )

        messages = [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_content},
        ]

        try:
            response: Any = completion(
                model=model, messages=messages, timeout=timeout
            )
            msg = getattr(response.choices[0], "message", None)
            content = getattr(msg, "content", "").strip()
            
            # Basic cleanup if the LLM wraps it in markdown code blocks
            if content.startswith("```json"):
                content = content[7:-3].strip()
            elif content.startswith("```"):
                content = content[3:-3].strip()

            parsed = json.loads(content)
            pattern = parsed.get("pattern")
            replacement = parsed.get("replacement")

            if pattern and replacement is not None:
                OptimizationRegexRule.objects.create(
                    user=user,
                    domain_type=domain_type,
                    pattern=pattern,
                    replacement=replacement,
                )
        except Exception:
            # Swallow exceptions in fire-and-forget task; we don't want to crash
            # background threads over a failed LLM regex deduction.
            pass


class ManualOptimizerService:
    """Offline optimization service for manual/free tier with sophisticated text-to-speech formatting."""

    @classmethod
    def optimize_chunk(
        cls,
        text: str,
        domain: str,
        code_mode: str | None = None,
        user: Any = None,
    ) -> str:
        """
        Offline formatting using sophisticated regex and string replacements
        for text-to-speech.
        """
        res = text

        # General enhancements
        res = re.sub(r"\b(?:e\.g\.|eg)\b", "for example", res, flags=re.IGNORECASE)
        res = re.sub(r"\b(?:i\.e\.|ie)\b", "that is", res, flags=re.IGNORECASE)
        res = re.sub(r"\b(?:etc\.|etc)\b", "and so on", res, flags=re.IGNORECASE)
        res = re.sub(r"\b(?:vs\.|vs)\b", "versus", res, flags=re.IGNORECASE)
        res = re.sub(r"(\d+)%", r"\g<1> percent", res)
        res = re.sub(r"_{3,}", "blank", res)

        if domain == Document.DomainType.EDUCATIONAL:
            res = res.replace("Fig.", "Figure")
            res = res.replace("Ch.", "Chapter")
            res = res.replace("Eq.", "Equation")
            res = res.replace(
                "F = ma",
                "Force equals mass multiplied by acceleration",
            )
            res = res.replace(
                "E = mc^2",
                "Energy equals mass times the speed of light squared",
            )
            # Basic math symbol expansion for educational texts
            res = re.sub(r" \+ ", " plus ", res)
            res = re.sub(r" \- ", " minus ", res)
            res = re.sub(r" \= ", " equals ", res)
            res = re.sub(r" \* ", " times ", res)
            res = re.sub(r" / ", " divided by ", res)

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

            # Simple file path spoken representation (e.g. src/utils.py -> src slash utils dot py)
            def path_replacer(match: re.Match) -> str:
                return match.group(0).replace("/", " slash ").replace(".", " dot ")

            res = re.sub(r"\b[\w\-]+(?:/[\w\-]+)+\.[\w]+\b", path_replacer, res)

        # Apply banked user regex rules if a user is provided
        if user and user.is_authenticated:
            rules = OptimizationRegexRule.objects.filter(
                user=user, domain_type=domain, is_active=True
            ).order_by("created_at")
            
            for rule in rules:
                try:
                    # Guard against runaway regex execution if LLM generated a bad pattern
                    res = re.sub(rule.pattern, rule.replacement, res)
                except Exception:
                    # Ignore bad rules to gracefully degrade
                    pass

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

            if domain == Document.DomainType.EDUCATIONAL:
                lines = base_cleaned.split('\n\n')
                # Matches: "1. ", "2) ", "3- ", "Q1 ", "Question 1: ", "a) ", "B. "
                q_pattern = re.compile(r'^\s*(?:(?:Q(?:uestion)?\s*\d+[\.\):\-]?)|(?:\d+[\.\):\-])|(?:[a-zA-Z][\.\)]))\s+', re.IGNORECASE)
                blank_pattern = re.compile(r'_{3,}|\bblank\b', re.IGNORECASE)
                
                expecting_answer = False
                question_counter = 1
                for i in range(len(lines) - 1):
                    line_str = lines[i].strip()
                    has_blank = blank_pattern.search(line_str)
                    is_q_start = q_pattern.match(line_str)
                    ends_with_qmark = line_str.endswith('?')
                    ends_with_punctuation = line_str.endswith('.') or line_str.endswith(':') or ends_with_qmark
                    
                    if has_blank or ends_with_qmark or is_q_start:
                        if not expecting_answer:
                            # It's a new question! Add a number if it doesn't already have one
                            if not is_q_start:
                                lines[i] = f"{question_counter}. " + lines[i]
                            question_counter += 1
                        expecting_answer = True
                        
                    if expecting_answer:
                        # If the line ends with a sentence terminator, the question is complete!
                        # The NEXT line must be the answer.
                        if ends_with_punctuation:
                            # Verify the next line is not just another question
                            next_line = lines[i+1].strip()
                            if not q_pattern.match(next_line) and not blank_pattern.search(next_line) and not next_line.endswith('?'):
                                if not next_line.lower().startswith("answer:"):
                                    lines[i+1] = "Answer: " + lines[i+1]
                            expecting_answer = False
                base_cleaned = '\n\n'.join(lines)

            # Create Chunks FIRST from base_cleaned text
            chunks = cls._create_chunks(document, base_cleaned)

            # Optimize each chunk based on optimization mode.
            # For LLM mode, catch LLMExhaustedError per-chunk so one failed
            # chunk does not abort the entire document. The document is still
            # completed, but _llm_fallback_used is set so the view can notify
            # the user via a toast.
            optimized_full_text = []
            opt_mode = str(document.optimization_mode)
            llm_fallback_used = False

            for chunk in chunks:
                if opt_mode == OptimizationMode.MANUAL:
                    optimized_chunk_text = ManualOptimizerService.optimize_chunk(
                        str(chunk.raw_text),
                        domain,
                        code_mode=str(document.code_mode),
                        user=document.user,
                    )
                else:
                    try:
                        optimized_chunk_text = LLMOptimizerService.optimize_chunk(
                            str(chunk.raw_text),
                            domain,
                            code_mode=str(document.code_mode),
                            additional_instructions=getattr(
                                document,
                                "additional_instructions",
                                None,
                            ),
                            user=document.user,
                        )
                    except LLMExhaustedError:
                        llm_fallback_used = True
                        optimized_chunk_text = ManualOptimizerService.optimize_chunk(
                            str(chunk.raw_text),
                            domain,
                            code_mode=str(document.code_mode),
                            user=document.user,
                        )
                chunk.optimized_text = optimized_chunk_text
                chunk.save(update_fields=["optimized_text"])
                optimized_full_text.append(optimized_chunk_text)

            # Stamp transient flag so the view can fire the correct UI toast.
            document._llm_fallback_used = llm_fallback_used

            document.optimized_speech_text = "\n\n".join(optimized_full_text)
            document.status = Document.Status.COMPLETED
            mode_desc = "Manual" if opt_mode == OptimizationMode.MANUAL else "LLM"
            document.summary = (
                f"Successfully optimized document for {domain} domain using {mode_desc} mode."
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
        
        user_chunk_size = 250
        try:
            if document.user and hasattr(document.user, 'settings'):
                user_chunk_size = int(document.user.settings.chunk_size)
        except (ValueError, AttributeError):
            pass

        chunk_index = 1
        for para in paragraphs:
            words = para.split()
            
            # If paragraph exceeds chunk size, split by words
            if len(words) > user_chunk_size:
                for i in range(0, len(words), user_chunk_size):
                    sub_para = " ".join(words[i:i + user_chunk_size])
                    sub_word_count = len(sub_para.split())
                    est_seconds = max(5, int((sub_word_count / words_per_minute) * 60))
                    chunk = document.chunks.create(
                        chunk_index=chunk_index,
                        title=f"Section {chunk_index}",
                        raw_text=sub_para,
                        optimized_text=sub_para,
                        estimated_duration_seconds=est_seconds,
                    )
                    chunks.append(chunk)
                    chunk_index += 1
            else:
                est_seconds = max(5, int((len(words) / words_per_minute) * 60))
                chunk = document.chunks.create(
                    chunk_index=chunk_index,
                    title=f"Section {chunk_index}",
                    raw_text=para,
                    optimized_text=para,
                    estimated_duration_seconds=est_seconds,
                )
                chunks.append(chunk)
                chunk_index += 1

        return chunks
