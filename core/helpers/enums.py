from django.db import models
from django.utils.translation import gettext_lazy as _


class DomainType(models.TextChoices):
    EDUCATIONAL = "educational", _("Educational")
    PROGRAMMING = "programming", _("Programming")
    AUTO_DETECT = "auto_detect", _("Auto Detect")


class Status(models.TextChoices):
    PENDING = "pending", _("Pending")
    PROCESSING = "processing", _("Processing")
    COMPLETED = "completed", _("Completed")
    FAILED = "failed", _("Failed")


class CodeMode(models.TextChoices):
    SKIP = "skip", _("Skip Code")
    SUMMARIZE = "summarize", _("Summarize Code")
    READ_CLEAN = "read_clean", _("Read Signature & Clean")


class OptimizationPreference(models.TextChoices):
    # Educational Prompts
    SIMPLIFY_TERMS = "simplify_terms", _("Simplify Academic Terms")
    DETAILED_MATH = "detailed_math", _("Detailed Math Descriptions")

    # Programming Prompts
    EXPLAIN_VARIABLES = "explain_vars", _("Explain Variable Names")
    SKIP_COMMENTS = "skip_comments", _("Skip Code Comments")


PREDEFINED_PROMPTS: dict[str, str] = {
    OptimizationPreference.SIMPLIFY_TERMS: "Replace complex academic jargon with simple, plain-English equivalents.",
    OptimizationPreference.DETAILED_MATH: "Read out all mathematical equations step-by-step in extreme detail.",
    OptimizationPreference.EXPLAIN_VARIABLES: "Whenever a variable is used, explain what it likely represents.",
    OptimizationPreference.SKIP_COMMENTS: "Do not read or summarize any code comments. Skip them entirely.",
}
