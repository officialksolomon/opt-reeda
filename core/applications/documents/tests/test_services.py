from django.test import TestCase

from core.applications.documents.models import Document
from core.applications.documents.services import BaseCleanerService
from core.applications.documents.services import EducationalOptimizerService
from core.applications.documents.services import PipelineService
from core.applications.documents.services import ProgrammingOptimizerService


class DocumentServicesTestCase(TestCase):
    def test_base_cleaner_removes_formatting_noise_and_urls(self):
        raw = """
        -----------------------------------
        Page 1 of 10
        Chapter 1: Intro..........
        For details visit https://example.com/docs?id=123.
        (Smith et al., 2024)
        """
        cleaned = BaseCleanerService.clean_formatting(raw)
        assert "-----------------------------------" not in cleaned
        assert "Page 1 of 10" not in cleaned
        assert "https://example.com" not in cleaned
        assert "Link to referenced resource" in cleaned
        assert "Smith and colleagues" in cleaned

    def test_educational_optimizer_expands_abbreviations_and_math(self):
        raw = "As shown in Fig. 1 of Ch. 4, F = ma holds true."
        optimized = EducationalOptimizerService.optimize(raw)
        assert "Figure 1" in optimized
        assert "Chapter 4" in optimized
        assert "Force equals mass multiplied by acceleration" in optimized

    def test_programming_optimizer_code_summarization(self):
        raw = "Here is Python code:\n```python\ndef add(a, b):\n    return a + b\n```\nExplanation follows."
        optimized = ProgrammingOptimizerService.optimize(
            raw,
            code_mode=Document.CodeMode.SUMMARIZE,
        )
        assert "[Code snippet containing 2 lines of source code.]" in optimized

    def test_programming_optimizer_code_skip(self):
        raw = "Here is Python code:\n```python\ndef add(a, b):\n    return a + b\n```\nExplanation follows."
        optimized = ProgrammingOptimizerService.optimize(
            raw,
            code_mode=Document.CodeMode.SKIP,
        )
        assert "[Source code section skipped for listening flow.]" in optimized

    def test_pipeline_service_end_to_end(self):
        doc = Document.objects.create(
            title="Educational Physics Unit",
            domain_type=Document.DomainType.EDUCATIONAL,
            raw_text="-------------------\nChapter 4: Dynamics\nAs seen in Fig. 2, F = ma.\n(Johnson, 2020)",
        )
        processed = PipelineService.process_document(doc)
        assert processed.status == Document.Status.COMPLETED
        assert (
            "Force equals mass multiplied by acceleration"
            in processed.optimized_speech_text
        )
        assert processed.chunks.count() >= 1
