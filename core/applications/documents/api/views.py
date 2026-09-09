from rest_framework import permissions
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
from core.applications.pricing.querysets import user_has_feature
from core.helpers.enums import OptimizationMode
from core.helpers.enums import OptimizationPreference


@document_viewset_schema
class DocumentViewSet(viewsets.ModelViewSet):
    queryset = Document.objects.with_chunks()
    serializer_class = DocumentSerializer
    parser_classes = (MultiPartParser, FormParser, JSONParser)
    permission_classes = [permissions.AllowAny]

    def get_queryset(self):
        qs = super().get_queryset()
        if self.action == "list":
            if self.request.user.is_authenticated:
                return qs.for_user(self.request.user)
            return qs.none()
        return qs

    def perform_create(self, serializer):
        user = self.request.user
        if user.is_authenticated:
            serializer.save(user=user)
        else:
            serializer.save(optimization_mode=OptimizationMode.MANUAL)

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
        if "optimization_mode" in serializer.validated_data:
            document.optimization_mode = serializer.validated_data["optimization_mode"]

        # Enforce Manual mode for users without the llm_optimization feature.
        # user_has_feature returns False for unauthenticated users without a DB hit.
        manual_mode_forced = not user_has_feature(request.user, "llm_optimization")
        if manual_mode_forced:
            document.optimization_mode = OptimizationMode.MANUAL

        document.save()

        processed_doc = PipelineService.process_document(document)
        response_serializer = DocumentSerializer(processed_doc)
        return Response(
            {
                **response_serializer.data,
                "manual_mode_forced": manual_mode_forced,
            },
            status=status.HTTP_200_OK,
        )

    @action(detail=True, methods=["get"])
    def chunks(self, request, pk=None):
        document = self.get_object()
        chunks = document.chunks.all()
        serializer = DocumentChunkSerializer(chunks, many=True)
        return Response(serializer.data, status=status.HTTP_200_OK)


@document_chunk_viewset_schema
class DocumentChunkViewSet(viewsets.ModelViewSet):
    serializer_class = DocumentChunkSerializer

    def get_queryset(self):
        qs = DocumentChunk.objects.with_document()
        if self.request.user.is_authenticated:
            return qs.filter(document__user=self.request.user)
        return qs.none()

    def perform_create(self, serializer):
        from rest_framework.exceptions import PermissionDenied
        document = serializer.validated_data.get('document')
        if document.user != self.request.user:
            raise PermissionDenied("You do not have permission to add chunks to this document.")
        serializer.save(is_user_created=True)

    def perform_destroy(self, instance):
        from rest_framework.exceptions import PermissionDenied
        if not instance.is_user_created:
            raise PermissionDenied("You can only delete chunks that you manually created.")
        instance.delete()
