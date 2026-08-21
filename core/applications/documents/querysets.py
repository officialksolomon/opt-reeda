from __future__ import annotations

from typing import TYPE_CHECKING

import auto_prefetch
from django.db import models

if TYPE_CHECKING:
    from core.applications.documents.models import Document  # noqa: F401
    from core.applications.documents.models import DocumentChunk  # noqa: F401


# ---------------------------------------------------------------------------
# Document
# ---------------------------------------------------------------------------


class DocumentQuerySet(models.QuerySet["Document"]):
    """Reusable query methods for the Document model."""

    def for_user(self, user: object) -> "DocumentQuerySet":
        """Scope documents to those owned by the given user."""
        return self.filter(user=user)

    def with_chunks(self) -> "DocumentQuerySet":
        """Prefetch related chunks. Used as the default base for the API ViewSet."""
        return self.prefetch_related("chunks")

    def with_audio(self) -> "DocumentQuerySet":
        """
        Return only documents that have at least one chunk with an audio
        recording, with chunks and their recordings prefetched.
        Used by AudioListView.
        """
        return (
            self.filter(chunks__audio_recording__isnull=False)
            .distinct()
            .prefetch_related("chunks", "chunks__audio_recording")
        )

    def apply_filters(
        self,
        q: str = "",
        status: str = "",
        domain_type: str = "",
        sort: str = "",
    ) -> "DocumentQuerySet":
        """
        Apply user-facing search, status, domain-type filters and sort ordering.
        All parameters are optional; omitting them returns the queryset unchanged.
        Used by DocumentFilterMixin, DocumentListView, and DocumentTableView.
        """
        qs = self

        if q:
            qs = qs.filter(title__icontains=q)
        if status:
            qs = qs.filter(status=status)
        if domain_type:
            qs = qs.filter(domain_type=domain_type)

        _SORT_MAP: dict[str, str | tuple[str, ...]] = {
            "oldest": "created_at",
            "title_asc": "title",
            "title_desc": "-title",
            "status": ("status", "-created_at"),
        }
        ordering = _SORT_MAP.get(sort, "-created_at")
        if isinstance(ordering, tuple):
            qs = qs.order_by(*ordering)
        else:
            qs = qs.order_by(ordering)

        return qs


# Manager proxies all QuerySet methods onto the manager itself.
DocumentManager = auto_prefetch.Manager.from_queryset(DocumentQuerySet)


# ---------------------------------------------------------------------------
# DocumentChunk
# ---------------------------------------------------------------------------


class DocumentChunkQuerySet(models.QuerySet["DocumentChunk"]):
    """Reusable query methods for the DocumentChunk model."""

    def ordered(self) -> "DocumentChunkQuerySet":
        """
        Return chunks ordered by chunk_index ascending.
        Used by DocumentDetailView, process_document_htmx, and the chunks
        action on DocumentViewSet.
        """
        return self.order_by("chunk_index")

    def with_document(self) -> "DocumentChunkQuerySet":
        """Select-related the parent Document. Used by DocumentChunkViewSet."""
        return self.select_related("document")


# Manager proxies all QuerySet methods onto the manager itself.
DocumentChunkManager = auto_prefetch.Manager.from_queryset(DocumentChunkQuerySet)
