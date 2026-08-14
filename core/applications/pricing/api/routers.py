from django.conf import settings
from rest_framework.routers import DefaultRouter, SimpleRouter
from core.applications.pricing.api.views import PlanViewSet, SubscriptionViewSet

if settings.DEBUG:
    router = DefaultRouter()
else:
    router = SimpleRouter()

router.register("plans", PlanViewSet, basename="plan")
router.register("subscriptions", SubscriptionViewSet, basename="subscription")

app_name = "pricing_api"
urlpatterns = router.urls
