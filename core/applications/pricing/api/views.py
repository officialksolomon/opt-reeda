from rest_framework import viewsets
from rest_framework.permissions import IsAdminUser
from rest_framework.permissions import IsAuthenticated

from core.applications.pricing.api.schemas import plan_viewset_schema
from core.applications.pricing.api.schemas import subscription_viewset_schema
from core.applications.pricing.api.serializers import PlanSerializer
from core.applications.pricing.api.serializers import SubscriptionSerializer
from core.applications.pricing.models import Plan
from core.applications.pricing.models import Subscription


@plan_viewset_schema
class PlanViewSet(viewsets.ModelViewSet):
    queryset = Plan.objects.with_full_details()
    serializer_class = PlanSerializer

    def get_permissions(self):
        if self.action in ["create", "update", "partial_update", "destroy"]:
            return [IsAdminUser()]
        return []


@subscription_viewset_schema
class SubscriptionViewSet(viewsets.ModelViewSet):
    serializer_class = SubscriptionSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        qs = Subscription.objects.with_relations()
        if self.request.user.is_staff:
            return qs
        return qs.for_user(self.request.user)

    def perform_create(self, serializer):
        serializer.save(user=self.request.user)
