from django.contrib import admin
from core.applications.documents.models import Document, DocumentChunk

class DocumentChunkInline(admin.TabularInline):
    model = DocumentChunk
    extra = 0
    fields = ("chunk_index", "title", "estimated_duration_seconds", "created_at")
    readonly_fields = ("chunk_index", "title", "estimated_duration_seconds", "created_at")

@admin.register(Document)
class DocumentAdmin(admin.ModelAdmin):
    list_display = ("title", "user", "domain_type", "status", "created_at")
    list_filter = ("status", "domain_type", "code_mode")
    search_fields = ("title", "user__email", "user__username")
    inlines = [DocumentChunkInline]

@admin.register(DocumentChunk)
class DocumentChunkAdmin(admin.ModelAdmin):
    list_display = ("document", "chunk_index", "title", "estimated_duration_seconds", "created_at")
    list_filter = ("document__domain_type",)
    search_fields = ("document__title", "title")
