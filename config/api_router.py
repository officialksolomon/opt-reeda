from django.conf import settings
from rest_framework.routers import DefaultRouter
from rest_framework.routers import SimpleRouter

from core.applications.documents.api.views import DocumentChunkViewSet
from core.applications.documents.api.views import DocumentViewSet
from core.applications.pricing.api.views import PlanViewSet, SubscriptionViewSet

router = DefaultRouter() if settings.DEBUG else SimpleRouter()

router.register("documents", DocumentViewSet, basename="documents")
router.register("chunks", DocumentChunkViewSet, basename="chunks")
router.register("plans", PlanViewSet, basename="plans")
router.register("subscriptions", SubscriptionViewSet, basename="subscriptions")

app_name = "api"
urlpatterns = router.urls
