from django.db import models
from django.utils.translation import gettext_lazy as _


class DomainType(models.TextChoices):
    EDUCATIONAL = "educational", _("Educational")
    PROGRAMMING = "programming", _("Programming")
    AUTO_DETECT = "auto_detect", _("Auto Detect")


class ChunkSize(models.TextChoices):
    SMALL = "100", _("Small (~100 words)")
    MEDIUM = "250", _("Medium (~250 words)")
    LARGE = "500", _("Large (~500 words)")


class TTSVoice(models.TextChoices):
    ALLOY = "alloy", _("Alloy (Neutral)")
    ECHO = "echo", _("Echo (Male)")
    FABLE = "fable", _("Fable (Male, British)")
    ONYX = "onyx", _("Onyx (Male, Deep)")
    NOVA = "nova", _("Nova (Female)")
    SHIMMER = "shimmer", _("Shimmer (Female)")


class Status(models.TextChoices):
    PENDING = "pending", _("Pending")
    PROCESSING = "processing", _("Processing")
    COMPLETED = "completed", _("Completed")
    FAILED = "failed", _("Failed")


class SubscriptionStatus(models.TextChoices):
    ACTIVE = "active", _("Active")
    CANCELED = "canceled", _("Canceled")
    PAST_DUE = "past_due", _("Past Due")


class TransactionStatus(models.TextChoices):
    PENDING = "pending", _("Pending")
    SUCCESS = "success", _("Success")
    FAILED = "failed", _("Failed")


class TransactionType(models.TextChoices):
    INITIAL = "initial", _("Initial")
    RENEWAL = "renewal", _("Renewal")
    UPGRADE = "upgrade", _("Upgrade")
    DOWNGRADE = "downgrade", _("Downgrade")


class CodeMode(models.TextChoices):
    SKIP = "skip", _("Skip Code")
    SUMMARIZE = "summarize", _("Summarize Code")
    READ_CLEAN = "read_clean", _("Read Signature & Clean")


class OptimizationMode(models.TextChoices):
    MANUAL = "manual", _("Manual")
    AI = "ai", _("AI")


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
