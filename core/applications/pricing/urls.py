from django.urls import path
from core.applications.pricing.views import PricingView, CheckoutView, PaystackWebhookView

app_name = "pricing"

urlpatterns = [
    path("", PricingView.as_view(), name="pricing"),
    path("checkout/", CheckoutView.as_view(), name="checkout"),
    path("webhook/paystack/", PaystackWebhookView.as_view(), name="webhook_paystack"),
]
