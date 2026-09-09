from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from django.db.models import ForeignKey
else:
    import auto_prefetch

    ForeignKey = auto_prefetch.ForeignKey

from django.conf import settings
from django.db import models
from django.db.models import CharField
from django.db.models import FileField
from django.db.models import JSONField
from django.db.models import PositiveIntegerField
from django.db.models import TextField
from django.utils.translation import gettext_lazy as _

from core.applications.documents.querysets import DocumentChunkManager
from core.applications.documents.querysets import DocumentManager
from core.helpers.enums import CodeMode
from core.helpers.enums import DomainType
from core.helpers.enums import OptimizationMode
from core.helpers.enums import Status
from core.helpers.models import TimeBasedModel


class Document(TimeBasedModel):  # type: ignore[django-manager-missing]
    objects = DocumentManager()

    if TYPE_CHECKING:
        chunks: models.Manager["DocumentChunk"]

    DomainType = DomainType
    Status = Status
    CodeMode = CodeMode
    OptimizationMode = OptimizationMode

    user = ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="documents",
    )

    title = CharField(max_length=255)
    file = FileField(upload_to="documents/", blank=True, null=True)
    file_type = CharField(max_length=20, default="txt")
    domain_type = CharField(
        max_length=30,
        choices=DomainType.choices,
        default=DomainType.AUTO_DETECT,
    )
    status = CharField(
        max_length=20,
        choices=Status.choices,
        default=Status.PENDING,
    )
    code_mode = CharField(
        max_length=20,
        choices=CodeMode.choices,
        default=CodeMode.SUMMARIZE,
    )
    optimization_mode = CharField(
        max_length=20,
        choices=OptimizationMode.choices,
        default=OptimizationMode.MANUAL,
    )
    additional_instructions = JSONField(
        default=list,
        blank=True,
        help_text=_("List of selected OptimizationPreference values."),
    )
    raw_text = TextField(blank=True)
    optimized_speech_text = TextField(blank=True)
    summary = TextField(blank=True)
    error_message = TextField(blank=True)

    class Meta(TimeBasedModel.Meta):
        verbose_name = _("Document")
        verbose_name_plural = _("Documents")
        ordering = ["-created_at"]

    if TYPE_CHECKING:

        def get_domain_type_display(self) -> str: ...

    def __str__(self) -> str:
        return f"{self.title} ({self.get_domain_type_display()})"


class DocumentChunk(TimeBasedModel):  # type: ignore[django-manager-missing]
    objects = DocumentChunkManager()

    document = ForeignKey(
        Document,
        on_delete=models.CASCADE,
        related_name="chunks",
    )
    chunk_index = PositiveIntegerField(default=0)
    title = CharField(_("Title"), max_length=255, blank=True)
    is_recording = models.BooleanField(default=False)
    raw_text = TextField(blank=True)
    optimized_text = TextField(blank=True)
    estimated_duration_seconds = PositiveIntegerField(default=0)

    class Meta(TimeBasedModel.Meta):
        verbose_name = _("Document Chunk")
        verbose_name_plural = _("Document Chunks")
        ordering = ["document", "chunk_index"]

    def __str__(self) -> str:
        return f"{self.document.title} - Chunk {self.chunk_index}"

    @property
    def highlighted_optimized_text(self) -> str:
        try:
            import difflib
            import re
            from django.utils.html import escape
            from django.utils.safestring import mark_safe

            if not self.raw_text or not self.optimized_text:
                return escape(self.optimized_text or "")

            def tokenize(text: str) -> list[str]:
                return re.findall(r'\S+|\s+', text)

            raw_tokens = tokenize(self.raw_text)
            opt_tokens = tokenize(self.optimized_text)

            sm = difflib.SequenceMatcher(None, raw_tokens, opt_tokens)
            result = []
            for tag, i1, i2, j1, j2 in sm.get_opcodes():
                if tag == 'equal':
                    result.append(escape("".join(opt_tokens[j1:j2])))
                elif tag in ('insert', 'replace'):
                    result.append(f'<mark class="bg-green-400 text-green-900 rounded">{escape("".join(opt_tokens[j1:j2]))}</mark>')

            return mark_safe("".join(result))
        except Exception as e:
            return f"Error: {e}"

    @property
    def highlighted_raw_text(self) -> str:
        try:
            import difflib
            import re
            from django.utils.html import escape
            from django.utils.safestring import mark_safe

            if not self.raw_text or not self.optimized_text:
                return escape(self.raw_text or "")

            def tokenize(text: str) -> list[str]:
                return re.findall(r'\S+|\s+', text)

            raw_tokens = tokenize(self.raw_text)
            opt_tokens = tokenize(self.optimized_text)

            sm = difflib.SequenceMatcher(None, raw_tokens, opt_tokens)
            result = []
            for tag, i1, i2, j1, j2 in sm.get_opcodes():
                if tag == 'equal':
                    result.append(escape("".join(raw_tokens[i1:i2])))
                elif tag in ('delete', 'replace'):
                    result.append(f'<del class="bg-red-200 text-red-900 rounded line-through">{escape("".join(raw_tokens[i1:i2]))}</del>')

            return mark_safe("".join(result))
        except Exception as e:
            return f"Error: {e}"


class ChunkAudioRecording(TimeBasedModel):
    chunk = models.OneToOneField(
        DocumentChunk,
        on_delete=models.CASCADE,
        related_name="audio_recording",
    )
    audio_file = models.FileField(upload_to="audio_chunks/")

    class Meta(TimeBasedModel.Meta):
        verbose_name = _("Chunk Audio Recording")
        verbose_name_plural = _("Chunk Audio Recordings")

    def __str__(self) -> str:
        return f"Audio for {self.chunk}"


class UserOptimizationExample(TimeBasedModel):
    user = ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="optimization_examples",
    )
    domain_type = CharField(max_length=30, choices=DomainType.choices)
    raw_text = TextField()
    edited_text = TextField()

    class Meta(TimeBasedModel.Meta):
        verbose_name = _("User Optimization Example")
        verbose_name_plural = _("User Optimization Examples")
        ordering = ["-created_at"]

    def __str__(self) -> str:
        return f"Example by {self.user} for {self.domain_type}"


class OptimizationRegexRule(TimeBasedModel):
    user = ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="regex_rules",
    )
    domain_type = CharField(max_length=30, choices=DomainType.choices)
    pattern = TextField()
    replacement = TextField(blank=True)
    is_active = models.BooleanField(default=True)

    class Meta(TimeBasedModel.Meta):
        verbose_name = _("Optimization Regex Rule")
        verbose_name_plural = _("Optimization Regex Rules")
        ordering = ["-created_at"]

    def __str__(self) -> str:
        return f"Regex Rule by {self.user} for {self.domain_type}"
