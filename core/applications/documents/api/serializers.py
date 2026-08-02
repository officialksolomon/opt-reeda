from rest_framework import serializers

from core.applications.documents.models import Document
from core.applications.documents.models import DocumentChunk


class DocumentChunkSerializer(serializers.ModelSerializer):
    class Meta:
        model = DocumentChunk
        fields = [
            "id",
            "chunk_index",
            "title",
            "raw_text",
            "optimized_text",
            "estimated_duration_seconds",
            "created_at",
            "updated_at",
        ]


class DocumentSerializer(serializers.ModelSerializer):
    chunks = DocumentChunkSerializer(many=True, read_only=True)
    domain_type_display = serializers.CharField(
        source="get_domain_type_display",
        read_only=True,
    )
    status_display = serializers.CharField(source="get_status_display", read_only=True)
    code_mode_display = serializers.CharField(
        source="get_code_mode_display",
        read_only=True,
    )

    class Meta:
        model = Document
        fields = [
            "id",
            "title",
            "file",
            "file_type",
            "domain_type",
            "domain_type_display",
            "status",
            "status_display",
            "code_mode",
            "code_mode_display",
            "raw_text",
            "optimized_speech_text",
            "summary",
            "error_message",
            "chunks",
            "created_at",
            "updated_at",
        ]
        read_only_fields = [
            "id",
            "status",
            "optimized_speech_text",
            "summary",
            "error_message",
            "created_at",
            "updated_at",
        ]


class DocumentProcessRequestSerializer(serializers.Serializer):
    domain_type = serializers.ChoiceField(
        choices=Document.DomainType.choices,
        default=Document.DomainType.AUTO_DETECT,
        required=False,
    )
    code_mode = serializers.ChoiceField(
        choices=Document.CodeMode.choices,
        default=Document.CodeMode.SUMMARIZE,
        required=False,
    )
