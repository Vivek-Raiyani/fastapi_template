"""Payment schemas."""

from datetime import datetime
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field


class CreatePaymentRequest(BaseModel):
    amount: int = Field(gt=0, description="Amount in smallest currency unit")
    currency: str = Field(default="INR", min_length=3, max_length=3)
    provider: Literal["razorpay", "stripe"] | None = None
    description: str | None = None


class VerifyRazorpayRequest(BaseModel):
    razorpay_order_id: str
    razorpay_payment_id: str
    razorpay_signature: str
    payment_id: int


class VerifyStripeRequest(BaseModel):
    session_id: str
    payment_id: int


class PaymentRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    amount: int
    currency: str
    provider: str
    provider_order_id: str | None
    provider_payment_id: str | None
    status: str
    description: str | None
    created_at: datetime
