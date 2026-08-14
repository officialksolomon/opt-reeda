from drf_spectacular.utils import extend_schema_view, extend_schema
from core.applications.pricing.api.serializers import PlanSerializer, SubscriptionSerializer

plan_viewset_schema = extend_schema_view(
    list=extend_schema(summary="List all plans", tags=["Plans"]),
    retrieve=extend_schema(summary="Retrieve a plan", tags=["Plans"]),
    create=extend_schema(summary="Create a plan", tags=["Plans"]),
    update=extend_schema(summary="Update a plan", tags=["Plans"]),
    partial_update=extend_schema(summary="Partial update a plan", tags=["Plans"]),
    destroy=extend_schema(summary="Delete a plan", tags=["Plans"]),
)

subscription_viewset_schema = extend_schema_view(
    list=extend_schema(summary="List all subscriptions", tags=["Subscriptions"]),
    retrieve=extend_schema(summary="Retrieve a subscription", tags=["Subscriptions"]),
    create=extend_schema(summary="Create a subscription", tags=["Subscriptions"]),
    update=extend_schema(summary="Update a subscription", tags=["Subscriptions"]),
    partial_update=extend_schema(summary="Partial update a subscription", tags=["Subscriptions"]),
    destroy=extend_schema(summary="Delete a subscription", tags=["Subscriptions"]),
)
