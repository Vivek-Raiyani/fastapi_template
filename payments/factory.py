"""Payment backend factory."""

from typing import Literal

from core.settings import settings
from payments.base import PaymentBackend
from payments.razorpay import RazorpayBackend
from payments.stripe import StripeBackend


def get_payment_backend(provider: Literal["razorpay", "stripe"] | None = None) -> PaymentBackend:
    chosen = provider or settings.PAYMENT_DEFAULT_PROVIDER
    if chosen == "stripe":
        return StripeBackend()
    return RazorpayBackend()
