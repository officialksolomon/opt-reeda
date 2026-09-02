import hmac
import hashlib
import requests
from django.conf import settings
from decimal import Decimal
from django.utils import timezone
from dateutil.relativedelta import relativedelta

class PaystackService:
    BASE_URL = "https://api.paystack.co"

    @classmethod
    def _get_headers(cls):
        return {
            "Authorization": f"Bearer {settings.PAYSTACK_SECRET_KEY}",
            "Content-Type": "application/json",
        }

    @classmethod
    def initialize_transaction(cls, email: str, amount: Decimal, reference: str, callback_url: str):
        """
        Initializes a Paystack transaction.
        Amount must be provided in NGN, it is converted to kobo for Paystack API.
        """
        url = f"{cls.BASE_URL}/transaction/initialize"
        payload = {
            "email": email,
            "amount": int(amount * 100),  # Paystack expects amounts in the smallest currency unit (kobo for NGN)
            "reference": reference,
            "callback_url": callback_url,
        }
        response = requests.post(url, json=payload, headers=cls._get_headers(), timeout=10)
        response.raise_for_status()
        return response.json()

    @classmethod
    def verify_transaction(cls, reference: str):
        """
        Verifies a transaction using the reference string.
        """
        url = f"{cls.BASE_URL}/transaction/verify/{reference}"
        response = requests.get(url, headers=cls._get_headers(), timeout=10)
        response.raise_for_status()
        return response.json()

    @classmethod
    def verify_webhook_signature(cls, payload: bytes, signature: str) -> bool:
        """
        Verifies the HMAC-SHA512 signature from a Paystack webhook.
        """
        secret = settings.PAYSTACK_SECRET_KEY.encode('utf-8')
        expected_signature = hmac.new(secret, payload, hashlib.sha512).hexdigest()
        return hmac.compare_digest(expected_signature, signature)

    @classmethod
    def calculate_proration_discount(cls, subscription) -> Decimal:
        """
        Calculates the unused value of the current subscription to be credited towards an upgrade.
        Returns a Decimal representing the discount.
        """
        if not subscription or not subscription.price or subscription.status != 'active':
            return Decimal("0.00")
            
        start = subscription.current_period_start or subscription.started_at
        end = subscription.current_period_end
        
        if not start or not end:
            # Try to calculate end if missing based on interval
            if not start:
                return Decimal("0.00")
            
            if subscription.price.interval == "month":
                end = start + relativedelta(months=1)
            elif subscription.price.interval == "year":
                end = start + relativedelta(years=1)
            else:
                return Decimal("0.00")
                
        now = timezone.now()
        
        if now >= end or now < start:
            return Decimal("0.00")
            
        total_seconds = (end - start).total_seconds()
        unused_seconds = (end - now).total_seconds()
        
        if total_seconds <= 0:
            return Decimal("0.00")
            
        ratio = Decimal(str(unused_seconds / total_seconds))
        discount = subscription.price.amount * ratio
        
        # Round to 2 decimal places
        return discount.quantize(Decimal("0.00"))
