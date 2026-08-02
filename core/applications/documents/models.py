from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from django.db.models import ForeignKey
else:
    import auto_prefetch

    ForeignKey = auto_prefetch.ForeignKey

from django.db import models
from django.db.models import CharField
from django.db.models import FileField
from django.db.models import JSONField
from django.db.models import PositiveIntegerField
from django.db.models import TextField
from django.utils.translation import gettext_lazy as _

from core.helpers.enums import CodeMode
from core.helpers.enums import DomainType
from core.helpers.enums import Status
from core.helpers.models import TimeBasedModel


class Document(TimeBasedModel):  # type: ignore[django-manager-missing]
    if TYPE_CHECKING:
        chunks: models.Manager[DocumentChunk]

    DomainType = DomainType
    Status = Status
    CodeMode = CodeMode

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


class DocumentChunk(TimeBasedModel):
    document = ForeignKey(
        Document,
        on_delete=models.CASCADE,
        related_name="chunks",
    )
    chunk_index = PositiveIntegerField(default=0)
    title = CharField(max_length=255, blank=True)
    raw_text = TextField(blank=True)
    optimized_text = TextField(blank=True)
    estimated_duration_seconds = PositiveIntegerField(default=0)

    class Meta(TimeBasedModel.Meta):
        verbose_name = _("Document Chunk")
        verbose_name_plural = _("Document Chunks")
        ordering = ["document", "chunk_index"]

    def __str__(self) -> str:
        return f"{self.document.title} - Chunk {self.chunk_index}"
