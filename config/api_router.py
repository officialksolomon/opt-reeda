from django.conf import settings
from rest_framework.routers import DefaultRouter
from rest_framework.routers import SimpleRouter

from core.applications.documents.api.views import DocumentChunkViewSet
from core.applications.documents.api.views import DocumentViewSet

router = DefaultRouter() if settings.DEBUG else SimpleRouter()

router.register("documents", DocumentViewSet, basename="documents")
router.register("chunks", DocumentChunkViewSet, basename="chunks")

app_name = "api"
urlpatterns = router.urls
