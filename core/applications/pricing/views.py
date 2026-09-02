from django.views.generic import TemplateView, View
from django.shortcuts import get_object_or_404, redirect
from django.urls import reverse
from django.contrib.auth.mixins import LoginRequiredMixin
from django.contrib import messages
from django.http import HttpResponse
from django.views.decorators.csrf import csrf_exempt
from django.utils.decorators import method_decorator
from django.utils import timezone
from decimal import Decimal
from dateutil.relativedelta import relativedelta

import json
import uuid
import logging

from core.applications.pricing.models import Plan, Price, Transaction, Subscription
from core.helpers.enums import TransactionStatus, SubscriptionStatus, TransactionType
from core.applications.pricing.services import PaystackService

logger = logging.getLogger(__name__)


class PricingView(TemplateView):
    template_name = "pages/pricing.html"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["plans"] = (
            Plan.objects.with_full_details().ordered_by_creation()
        )
        return context


class CheckoutView(LoginRequiredMixin, View):
    def post(self, request, *args, **kwargs):
        price_id = request.POST.get("price_id")
        price = get_object_or_404(Price, id=price_id, is_active=True)
        
        prorated_discount = Decimal("0.00")
        transaction_type = TransactionType.INITIAL
        base_amount = price.amount
        
        # Determine the user's subscription or create a shell if they don't have one
        subscription = request.user.subscriptions.first()
        if subscription and subscription.status == SubscriptionStatus.ACTIVE:
            transaction_type = TransactionType.UPGRADE
            prorated_discount = PaystackService.calculate_proration_discount(subscription)
        elif not subscription:
            subscription = Subscription.objects.create(
                user=request.user,
                price=price,
                status=SubscriptionStatus.PAST_DUE  # Will be set to ACTIVE upon payment
            )
            
        final_amount = max(Decimal("0.00"), base_amount - prorated_discount)
        
        reference = f"ps_{uuid.uuid4().hex[:12]}"
        
        # Create transaction
        Transaction.objects.create(
            user=request.user,
            subscription=subscription,
            price=price,
            type=transaction_type,
            base_amount=base_amount,
            prorated_discount=prorated_discount,
            amount=final_amount,
            reference=reference,
            status=TransactionStatus.PENDING
        )
        
        callback_url = request.build_absolute_uri(reverse("pricing:pricing"))
        
        try:
            paystack_response = PaystackService.initialize_transaction(
                email=request.user.email,
                amount=final_amount,
                reference=reference,
                callback_url=callback_url
            )
            
            if paystack_response.get("status"):
                auth_url = paystack_response["data"]["authorization_url"]
                return redirect(auth_url)
            else:
                messages.error(request, "Could not initialize payment.")
                return redirect("pricing:pricing")
        except Exception as e:
            logger.error(f"Paystack initialization error: {e}")
            messages.error(request, "Payment gateway error.")
            return redirect("pricing:pricing")


@method_decorator(csrf_exempt, name="dispatch")
class PaystackWebhookView(View):
    def post(self, request, *args, **kwargs):
        payload = request.body
        signature = request.headers.get("x-paystack-signature")
        
        if not signature or not PaystackService.verify_webhook_signature(payload, signature):
            return HttpResponse("Invalid signature", status=400)
            
        try:
            event = json.loads(payload)
        except json.JSONDecodeError:
            return HttpResponse("Invalid payload", status=400)
            
        if event.get("event") == "charge.success":
            data = event.get("data", {})
            reference = data.get("reference")
            
            try:
                # Optionally call API to verify again just to be safe
                verification = PaystackService.verify_transaction(reference)
                if verification.get("data", {}).get("status") == "success":
                    transaction = Transaction.objects.get(reference=reference)
                    transaction.status = TransactionStatus.SUCCESS
                    transaction.save()
                    
                    # Update subscription
                    subscription = transaction.subscription
                    
                    if subscription:
                        subscription.status = SubscriptionStatus.ACTIVE
                        subscription.price = transaction.price
                        subscription.started_at = timezone.now()
                        subscription.current_period_start = timezone.now()
                        
                        if transaction.price.interval == "month":
                            subscription.current_period_end = timezone.now() + relativedelta(months=1)
                        elif transaction.price.interval == "year":
                            subscription.current_period_end = timezone.now() + relativedelta(years=1)
                            
                        subscription.save()
                    else:
                        end_date = timezone.now() + relativedelta(months=1) if transaction.price.interval == "month" else timezone.now() + relativedelta(years=1)
                        Subscription.objects.create(
                            user=transaction.user,
                            price=transaction.price,
                            status=SubscriptionStatus.ACTIVE,
                            started_at=timezone.now(),
                            current_period_start=timezone.now(),
                            current_period_end=end_date
                        )
            except Transaction.DoesNotExist:
                logger.error(f"Transaction with ref {reference} not found.")
            except Exception as e:
                logger.error(f"Error handling webhook for {reference}: {e}")
                
        return HttpResponse("OK", status=200)
