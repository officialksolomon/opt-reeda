from unittest.mock import MagicMock
from unittest.mock import patch

from django.contrib.auth import get_user_model
from django.test import TestCase

from core.applications.documents.models import Document
from core.applications.documents.models import OptimizationRegexRule
from core.applications.documents.models import UserOptimizationExample
from core.applications.documents.services import BaseCleanerService
from core.applications.documents.services import LLMExhaustedError
from core.applications.documents.services import LLMOptimizerService
from core.applications.documents.services import ManualOptimizerService
from core.applications.documents.services import PipelineService
from core.applications.documents.services import UserOptimizationExampleService

User = get_user_model()


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
        """
        Educational abbreviation expansion is a ManualOptimizerService concern.
        Tested directly — no API key required.
        """
        raw = "As shown in Fig. 1 of Ch. 4, F = ma holds true."
        optimized = ManualOptimizerService.optimize_chunk(
            raw, domain=Document.DomainType.EDUCATIONAL
        )
        assert "Figure 1" in optimized
        assert "Chapter 4" in optimized
        assert "Force equals mass multiplied by acceleration" in optimized

    def test_programming_optimizer_code_summarization(self):
        """Code summarization marker is produced by ManualOptimizerService."""
        raw = "Here is Python code:\n```python\ndef add(a, b):\n    return a + b\n```\nExplanation follows."
        optimized = ManualOptimizerService.optimize_chunk(
            raw,
            domain=Document.DomainType.PROGRAMMING,
            code_mode=Document.CodeMode.SUMMARIZE,
        )
        assert "[Code snippet containing 2 lines of source code.]" in optimized

    def test_programming_optimizer_code_skip(self):
        """Code skip marker is produced by ManualOptimizerService."""
        raw = "Here is Python code:\n```python\ndef add(a, b):\n    return a + b\n```\nExplanation follows."
        optimized = ManualOptimizerService.optimize_chunk(
            raw,
            domain=Document.DomainType.PROGRAMMING,
            code_mode=Document.CodeMode.SKIP,
        )
        assert "[Source code section skipped for listening flow.]" in optimized

    def test_llm_optimizer_raises_exhausted_when_api_unavailable(self):
        """LLMOptimizerService raises LLMExhaustedError after all retries fail."""
        with self.assertRaises(LLMExhaustedError):
            LLMOptimizerService.optimize_chunk(
                "Test text.", domain=Document.DomainType.EDUCATIONAL
            )

    def test_llm_optimizer_returns_content_on_success(self):
        """LLMOptimizerService returns the LLM response content on success."""
        mock_response = MagicMock()
        mock_response.choices[0].message.content = "Optimized text."
        with patch(
            "core.applications.documents.services.completion",
            return_value=mock_response,
        ):
            result = LLMOptimizerService.optimize_chunk(
                "Raw text.", domain=Document.DomainType.EDUCATIONAL
            )
        assert result == "Optimized text."

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

    def test_capture_example_prunes_old_examples(self):
        """UserOptimizationExampleService keeps max 5 examples per user/domain."""
        user = User.objects.create_user("testuser", "test@test.com", "pass")
        for i in range(7):
            UserOptimizationExampleService.capture_example(
                user=user,
                domain_type=Document.DomainType.PROGRAMMING,
                raw_text=f"raw {i}",
                edited_text=f"edited {i}",
            )
        
        examples = UserOptimizationExample.objects.filter(
            user=user, domain_type=Document.DomainType.PROGRAMMING
        ).order_by("created_at")
        
        self.assertEqual(examples.count(), 5)
        # The oldest (0 and 1) should have been pruned.
        self.assertEqual(examples.first().raw_text, "raw 2")
        self.assertEqual(examples.last().raw_text, "raw 6")

    def test_manual_optimizer_applies_active_regex_rule(self):
        """ManualOptimizerService applies banked user regex rules."""
        user = User.objects.create_user("testuser2", "test2@test.com", "pass")
        OptimizationRegexRule.objects.create(
            user=user,
            domain_type=Document.DomainType.EDUCATIONAL,
            pattern=r"\bAI\b",
            replacement="Artificial Intelligence",
            is_active=True,
        )
        
        raw_text = "The AI will help us."
        optimized = ManualOptimizerService.optimize_chunk(
            raw_text,
            domain=Document.DomainType.EDUCATIONAL,
            user=user,
        )
        self.assertEqual(optimized, "The Artificial Intelligence will help us.")

    def test_manual_optimizer_ignores_invalid_regex_rule(self):
        """ManualOptimizerService gracefully handles invalid user regex rules."""
        user = User.objects.create_user("testuser3", "test3@test.com", "pass")
        OptimizationRegexRule.objects.create(
            user=user,
            domain_type=Document.DomainType.EDUCATIONAL,
            pattern=r"(unclosed group",
            replacement="break",
            is_active=True,
        )
        
        raw_text = "The AI will help us."
        optimized = ManualOptimizerService.optimize_chunk(
            raw_text,
            domain=Document.DomainType.EDUCATIONAL,
            user=user,
        )
        # Should not raise an exception, and should return original text unaffected by the bad rule.
        self.assertEqual(optimized, raw_text)
