from rest_framework import serializers
from core.applications.pricing.models import Plan, Price, Subscription, Feature, PlanFeature


class FeatureSerializer(serializers.ModelSerializer):
    class Meta:
        model = Feature
        fields = ["id", "name", "key", "value_type"]


class PlanFeatureSerializer(serializers.ModelSerializer):
    feature = FeatureSerializer(read_only=True)

    class Meta:
        model = PlanFeature
        fields = ["feature", "value"]


class PriceSerializer(serializers.ModelSerializer):
    class Meta:
        model = Price
        fields = ["id", "amount", "currency", "interval", "is_active", "created_at", "updated_at"]


class PlanSerializer(serializers.ModelSerializer):
    prices = PriceSerializer(many=True, read_only=True)
    features = PlanFeatureSerializer(many=True, read_only=True)

    class Meta:
        model = Plan
        fields = ["id", "name", "slug", "description", "is_active", "features", "prices", "created_at", "updated_at"]


class SubscriptionSerializer(serializers.ModelSerializer):
    class Meta:
        model = Subscription
        fields = ["id", "user", "price", "status", "started_at", "current_period_start", "current_period_end", "canceled_at", "created_at", "updated_at"]
        read_only_fields = ["user", "started_at"]
