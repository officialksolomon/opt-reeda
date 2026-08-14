from rest_framework import viewsets
from rest_framework.permissions import IsAuthenticated, IsAdminUser
from core.applications.pricing.models import Plan, Subscription
from core.applications.pricing.api.serializers import PlanSerializer, SubscriptionSerializer
from core.applications.pricing.api.schemas import plan_viewset_schema, subscription_viewset_schema


@plan_viewset_schema
class PlanViewSet(viewsets.ModelViewSet):
    queryset = Plan.objects.prefetch_related("prices", "features", "features__feature").all()
    serializer_class = PlanSerializer
    
    def get_permissions(self):
        if self.action in ['create', 'update', 'partial_update', 'destroy']:
            return [IsAdminUser()]
        return []


@subscription_viewset_schema
class SubscriptionViewSet(viewsets.ModelViewSet):
    serializer_class = SubscriptionSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        if self.request.user.is_staff:
            return Subscription.objects.select_related("user", "price", "price__plan").all()
        return Subscription.objects.select_related("user", "price", "price__plan").filter(user=self.request.user)

    def perform_create(self, serializer):
        serializer.save(user=self.request.user)
