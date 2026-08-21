from django.contrib import admin
from core.applications.pricing.models import Plan, Feature, PlanFeature, Price, Subscription

@admin.register(Plan)
class PlanAdmin(admin.ModelAdmin):
    list_display = ("name", "slug", "is_active", "created_at")
    search_fields = ("name", "slug")
    list_filter = ("is_active",)
    prepopulated_fields = {"slug": ("name",)}

@admin.register(Feature)
class FeatureAdmin(admin.ModelAdmin):
    list_display = ("name", "key", "value_type", "created_at")
    search_fields = ("name", "key")
    prepopulated_fields = {"key": ("name",)}

@admin.register(PlanFeature)
class PlanFeatureAdmin(admin.ModelAdmin):
    list_display = ("plan", "feature", "value", "created_at")
    list_filter = ("plan", "feature")

@admin.register(Price)
class PriceAdmin(admin.ModelAdmin):
    list_display = ("plan", "amount", "currency", "interval", "is_active", "created_at")
    list_filter = ("interval", "is_active", "plan")

@admin.register(Subscription)
class SubscriptionAdmin(admin.ModelAdmin):
    list_display = ("user", "price", "status", "started_at", "current_period_end")
    list_filter = ("status", "price__plan")
    search_fields = ("user__email", "user__username")
