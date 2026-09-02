from django.conf import settings
from django.db import models
from django.db.models import CharField, BooleanField, DecimalField, DateTimeField, JSONField, SlugField
from django.utils.translation import gettext_lazy as _
from typing import TYPE_CHECKING
from core.helpers.models import TimeBasedModel
from core.helpers.enums import SubscriptionStatus, TransactionStatus, TransactionType
from core.applications.pricing.querysets import PlanManager, SubscriptionManager

if TYPE_CHECKING:
    from django.db.models import ForeignKey
else:
    import auto_prefetch
    ForeignKey = auto_prefetch.ForeignKey


class Plan(TimeBasedModel):  # type: ignore[django-manager-missing]
    objects = PlanManager()

    name = CharField(max_length=100)
    slug = SlugField(unique=True)
    description = CharField(max_length=255, blank=True)
    is_active = BooleanField(default=True)

    class Meta(TimeBasedModel.Meta):
        verbose_name = _("Plan")
        verbose_name_plural = _("Plans")

    def __str__(self) -> str:
        return self.name


class Feature(TimeBasedModel):
    name = CharField(max_length=100)
    key = SlugField(unique=True)
    value_type = CharField(max_length=20, help_text=_("E.g., integer, boolean, string"))

    class Meta(TimeBasedModel.Meta):
        verbose_name = _("Feature")
        verbose_name_plural = _("Features")

    def __str__(self) -> str:
        return self.name


class PlanFeature(TimeBasedModel):
    plan = ForeignKey(Plan, on_delete=models.CASCADE, related_name="features")
    feature = ForeignKey(Feature, on_delete=models.CASCADE)
    value = JSONField()

    class Meta(TimeBasedModel.Meta):
        verbose_name = _("Plan Feature")
        verbose_name_plural = _("Plan Features")
        unique_together = ("plan", "feature")

    def __str__(self) -> str:
        return f"{self.plan.name} - {self.feature.name}"


class Price(TimeBasedModel):
    plan = ForeignKey(Plan, on_delete=models.CASCADE, related_name="prices")
    amount = DecimalField(max_digits=10, decimal_places=2, default=0.00)
    currency = CharField(max_length=10, default="NGN")
    interval = CharField(max_length=20, default="month", help_text=_("E.g., month, year, forever"))
    is_active = BooleanField(default=True)

    class Meta(TimeBasedModel.Meta):
        verbose_name = _("Price")
        verbose_name_plural = _("Prices")

    def __str__(self) -> str:
        return f"{self.plan.name} - {self.amount} {self.currency}/{self.interval}"


class Subscription(TimeBasedModel):  # type: ignore[django-manager-missing]
    objects = SubscriptionManager()

    user = ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="subscriptions")
    price = ForeignKey(Price, on_delete=models.RESTRICT, related_name="subscriptions")
    status = CharField(max_length=20, choices=SubscriptionStatus.choices, default=SubscriptionStatus.ACTIVE, help_text=_("E.g., active, canceled, past_due"))
    started_at = DateTimeField(auto_now_add=True)
    current_period_start = DateTimeField(null=True, blank=True)
    current_period_end = DateTimeField(null=True, blank=True)
    canceled_at = DateTimeField(null=True, blank=True)

    class Meta(TimeBasedModel.Meta):
        verbose_name = _("Subscription")
        verbose_name_plural = _("Subscriptions")

    def __str__(self) -> str:
        return f"{self.user.username} - {self.price.plan.name}"


class Transaction(TimeBasedModel):
    user = ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="transactions")
    subscription = ForeignKey(Subscription, on_delete=models.CASCADE, related_name="transactions", null=True, blank=True)
    price = ForeignKey(Price, on_delete=models.RESTRICT, related_name="transactions")
    type = CharField(max_length=20, choices=TransactionType.choices, default=TransactionType.INITIAL)
    base_amount = DecimalField(max_digits=10, decimal_places=2, default=0.00, help_text=_("The original price of the new plan"))
    prorated_discount = DecimalField(max_digits=10, decimal_places=2, default=0.00, help_text=_("Discount applied from unused previous plan time"))
    amount = DecimalField(max_digits=10, decimal_places=2, default=0.00, help_text=_("The final amount charged (base_amount - prorated_discount)"))
    reference = CharField(max_length=100, unique=True, help_text=_("Paystack transaction reference"))
    status = CharField(max_length=20, choices=TransactionStatus.choices, default=TransactionStatus.PENDING)

    class Meta(TimeBasedModel.Meta):
        verbose_name = _("Transaction")
        verbose_name_plural = _("Transactions")

    def __str__(self) -> str:
        return f"{self.user.username} - {self.reference} - {self.status}"
