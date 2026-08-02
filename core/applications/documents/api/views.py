from rest_framework import status
from rest_framework import viewsets
from rest_framework.decorators import action
from rest_framework.parsers import FormParser
from rest_framework.parsers import JSONParser
from rest_framework.parsers import MultiPartParser
from rest_framework.response import Response

from core.applications.documents.api.schemas import document_chunk_viewset_schema
from core.applications.documents.api.schemas import document_viewset_schema
from core.applications.documents.api.serializers import DocumentChunkSerializer
from core.applications.documents.api.serializers import DocumentProcessRequestSerializer
from core.applications.documents.api.serializers import DocumentSerializer
from core.applications.documents.models import Document
from core.applications.documents.models import DocumentChunk
from core.applications.documents.services import PipelineService
from core.helpers.enums import OptimizationPreference


@document_viewset_schema
class DocumentViewSet(viewsets.ModelViewSet):
    queryset = Document.objects.all().prefetch_related("chunks")
    serializer_class = DocumentSerializer
    parser_classes = (MultiPartParser, FormParser, JSONParser)

    @action(detail=False, methods=["get"])
    def optimization_preferences(self, request):
        """Returns the list of available additional instructions (preferences)."""
        preferences = [
            {"key": key, "label": str(label)}
            for key, label in OptimizationPreference.choices
        ]
        return Response(preferences, status=status.HTTP_200_OK)

    @action(
        detail=True,
        methods=["post"],
        serializer_class=DocumentProcessRequestSerializer,
    )
    def process(self, request, pk=None):
        document = self.get_object()
        serializer = DocumentProcessRequestSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        if "domain_type" in serializer.validated_data:
            document.domain_type = serializer.validated_data["domain_type"]
        if "code_mode" in serializer.validated_data:
            document.code_mode = serializer.validated_data["code_mode"]
        document.save()

        processed_doc = PipelineService.process_document(document)
        response_serializer = DocumentSerializer(processed_doc)
        return Response(response_serializer.data, status=status.HTTP_200_OK)

    @action(detail=True, methods=["get"])
    def chunks(self, request, pk=None):
        document = self.get_object()
        chunks = document.chunks.all()
        serializer = DocumentChunkSerializer(chunks, many=True)
        return Response(serializer.data, status=status.HTTP_200_OK)


@document_chunk_viewset_schema
class DocumentChunkViewSet(viewsets.ReadOnlyModelViewSet):
    queryset = DocumentChunk.objects.select_related("document")
    serializer_class = DocumentChunkSerializer
