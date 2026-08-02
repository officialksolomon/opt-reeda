"""OpenAPI schema definitions for the documents API."""

from drf_spectacular.utils import extend_schema
from drf_spectacular.utils import extend_schema_view

document_viewset_schema = extend_schema_view(
    list=extend_schema(tags=["Documents"], summary="List all uploaded documents"),
    retrieve=extend_schema(
        tags=["Documents"],
        summary="Retrieve a specific document by ID",
    ),
    create=extend_schema(
        tags=["Documents"],
        summary="Upload and create a new document",
    ),
    update=extend_schema(tags=["Documents"], summary="Replace a document"),
    partial_update=extend_schema(
        tags=["Documents"],
        summary="Partially update a document",
    ),
    destroy=extend_schema(tags=["Documents"], summary="Delete a document"),
    process=extend_schema(
        tags=["Documents"],
        summary="Trigger optimization processing on a document",
        description="Applies baseline cleanup and domain-specific (Educational or Programming) speech optimizations.",
    ),
    chunks=extend_schema(
        tags=["Documents"],
        summary="Retrieve playback audio chunks for a document",
        description="Returns section chunks with estimated reading durations for player navigation.",
    ),
)

document_chunk_viewset_schema = extend_schema_view(
    list=extend_schema(tags=["Document Chunks"], summary="List all document chunks"),
    retrieve=extend_schema(
        tags=["Document Chunks"],
        summary="Retrieve a specific chunk by ID",
    ),
)
