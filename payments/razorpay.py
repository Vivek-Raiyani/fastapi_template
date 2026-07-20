"""Razorpay payment backend."""

import hashlib
import hmac
import json
from typing import Any

import razorpay

from core.settings import settings


class RazorpayBackend:
    provider = "razorpay"

    def __init__(self):
        if not settings.razorpay_enabled:
            raise ValueError("Razorpay credentials not configured")
        self._client = razorpay.Client(auth=(settings.RAZORPAY_KEY_ID, settings.RAZORPAY_KEY_SECRET))

    async def create_order(
        self,
        *,
        amount: int,
        currency: str,
        receipt: str,
        notes: dict[str, str] | None = None,
    ) -> dict[str, Any]:
        order = self._client.order.create(
            {"amount": amount, "currency": currency, "receipt": receipt, "notes": notes or {}}
        )
        return {
            "provider": self.provider,
            "order_id": order["id"],
            "amount": order["amount"],
            "currency": order["currency"],
            "key_id": settings.RAZORPAY_KEY_ID,
        }

    async def verify_payment(
        self,
        *,
        razorpay_order_id: str,
        razorpay_payment_id: str,
        razorpay_signature: str,
    ) -> dict[str, Any]:
        self._client.utility.verify_payment_signature(
            {
                "razorpay_order_id": razorpay_order_id,
                "razorpay_payment_id": razorpay_payment_id,
                "razorpay_signature": razorpay_signature,
            }
        )
        return {
            "provider": self.provider,
            "order_id": razorpay_order_id,
            "payment_id": razorpay_payment_id,
            "status": "paid",
        }

    def verify_webhook(self, body: bytes, signature: str) -> dict[str, Any]:
        secret = settings.RAZORPAY_WEBHOOK_SECRET
        if not secret:
            raise ValueError("RAZORPAY_WEBHOOK_SECRET not configured")
        expected = hmac.new(secret.encode(), body, hashlib.sha256).hexdigest()
        if not hmac.compare_digest(expected, signature):
            raise ValueError("Invalid Razorpay webhook signature")
        return json.loads(body)
