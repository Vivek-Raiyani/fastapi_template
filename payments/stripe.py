"""Stripe payment backend."""

from typing import Any

import stripe

from core.settings import settings


class StripeBackend:
    provider = "stripe"

    def __init__(self):
        if not settings.stripe_enabled:
            raise ValueError("Stripe credentials not configured")
        stripe.api_key = settings.STRIPE_SECRET_KEY

    async def create_order(
        self,
        *,
        amount: int,
        currency: str,
        receipt: str,
        notes: dict[str, str] | None = None,
    ) -> dict[str, Any]:
        session = stripe.checkout.Session.create(
            mode="payment",
            line_items=[
                {
                    "price_data": {
                        "currency": currency.lower(),
                        "unit_amount": amount,
                        "product_data": {
                            "name": notes.get("description", "Payment") if notes else "Payment"
                        },
                    },
                    "quantity": 1,
                }
            ],
            success_url=f"{settings.BASE_URL}/payments/success?session_id={{CHECKOUT_SESSION_ID}}",
            cancel_url=f"{settings.BASE_URL}/payments/cancel",
            metadata={"receipt": receipt, **(notes or {})},
        )
        return {
            "provider": self.provider,
            "order_id": session.id,
            "amount": amount,
            "currency": currency,
            "checkout_url": session.url,
            "publishable_key": settings.STRIPE_PUBLISHABLE_KEY,
        }

    async def verify_payment(self, *, session_id: str) -> dict[str, Any]:
        session = stripe.checkout.Session.retrieve(session_id)
        if session.payment_status != "paid":
            return {
                "provider": self.provider,
                "order_id": session_id,
                "status": session.payment_status,
            }
        return {
            "provider": self.provider,
            "order_id": session_id,
            "payment_id": session.payment_intent,
            "status": "paid",
        }

    def verify_webhook(self, body: bytes, signature: str) -> dict:
        event = stripe.Webhook.construct_event(body, signature, settings.STRIPE_WEBHOOK_SECRET)
        return {"type": event.type, "data": {"object": dict(event.data.object)}}
