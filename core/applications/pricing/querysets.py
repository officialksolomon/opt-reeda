from __future__ import annotations

from typing import TYPE_CHECKING

import auto_prefetch
from django.db import models

if TYPE_CHECKING:
    from core.applications.pricing.models import Plan  # noqa: F401
    from core.applications.pricing.models import Subscription  # noqa: F401


# ---------------------------------------------------------------------------
# Plan
# ---------------------------------------------------------------------------


class PlanQuerySet(models.QuerySet["Plan"]):
    """Reusable query methods for the Plan model."""

    def active(self) -> "PlanQuerySet":
        """Return only active plans."""
        return self.filter(is_active=True)

    def with_full_details(self) -> "PlanQuerySet":
        """
        Prefetch prices, features, and nested feature details.
        Used by both the pricing page template and the API PlanViewSet.
        """
        return self.prefetch_related("prices", "features", "features__feature")

    def ordered_by_creation(self) -> "PlanQuerySet":
        """Return plans ordered oldest-first (pricing page display order)."""
        return self.order_by("created_at")


# Manager proxies all QuerySet methods onto the manager itself.
PlanManager = auto_prefetch.Manager.from_queryset(PlanQuerySet)


# ---------------------------------------------------------------------------
# Subscription
# ---------------------------------------------------------------------------


class SubscriptionQuerySet(models.QuerySet["Subscription"]):
    """Reusable query methods for the Subscription model."""

    def for_user(self, user: object) -> "SubscriptionQuerySet":
        """Scope subscriptions to a specific user."""
        return self.filter(user=user)

    def active(self) -> "SubscriptionQuerySet":
        """Return only active subscriptions."""
        return self.filter(status="active")

    def with_relations(self) -> "SubscriptionQuerySet":
        """Select-related user, price, and plan for detail-heavy views/serializers."""
        return self.select_related("user", "price", "price__plan")

    def with_feature(self, feature_key: str) -> "SubscriptionQuerySet":
        """
        Filter to subscriptions whose plan grants the given feature key as True.
        Used by user_has_feature and any future feature-gate checks.
        """
        return self.filter(
            price__plan__features__feature__key=feature_key,
            price__plan__features__value=True,
        )


# Manager proxies all QuerySet methods onto the manager itself.
SubscriptionManager = auto_prefetch.Manager.from_queryset(SubscriptionQuerySet)


# ---------------------------------------------------------------------------
# Feature-gate helper
# ---------------------------------------------------------------------------


def user_has_feature(user: object, feature_key: str) -> bool:
    """
    Single, canonical check for whether a user has an active subscription
    that grants a specific feature.

    Defined here because feature-gating is a pricing-domain concern — the
    Subscription model lives in this app.  Import this function from any
    other app that needs a feature gate; do not redefine the query elsewhere.

    Returns False for unauthenticated users without querying the database.
    """
    from core.applications.pricing.models import Subscription  # noqa: PLC0415

    if not getattr(user, "is_authenticated", False):
        return False

    return (
        Subscription.objects.active()
        .for_user(user)
        .with_feature(feature_key)
        .exists()
    )
