"""Payment API routes."""

from fastapi import APIRouter, Depends, Header, Request
from sqlalchemy.ext.asyncio import AsyncSession

from core.dependencies import get_current_user, get_db
from core.permissions import PermissionCodename, require_permission
from database.models.user import User
from modules.payments.schemas import (
    CreatePaymentRequest,
    PaymentRead,
    VerifyRazorpayRequest,
    VerifyStripeRequest,
)
from modules.payments.service import PaymentService

router = APIRouter(prefix="/payments", tags=["payments"])


@router.post("/create-order")
async def create_order(
    data: CreatePaymentRequest,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
):
    service = PaymentService(db)
    return await service.create_payment(user, data)


@router.post("/verify/razorpay", response_model=PaymentRead)
async def verify_razorpay(
    data: VerifyRazorpayRequest,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
):
    service = PaymentService(db)
    return await service.verify_razorpay(
        user,
        payment_id=data.payment_id,
        razorpay_order_id=data.razorpay_order_id,
        razorpay_payment_id=data.razorpay_payment_id,
        razorpay_signature=data.razorpay_signature,
    )


@router.post("/verify/stripe", response_model=PaymentRead)
async def verify_stripe(
    data: VerifyStripeRequest,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
):
    service = PaymentService(db)
    return await service.verify_stripe(user, payment_id=data.payment_id, session_id=data.session_id)


@router.get("/{payment_id}", response_model=PaymentRead)
async def get_payment(
    payment_id: int,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(require_permission(PermissionCodename.PAYMENTS_VIEW.value)),
):
    service = PaymentService(db)
    payment = await service._get_user_payment(user, payment_id)
    return payment


@router.post("/webhook/razorpay")
async def razorpay_webhook(
    request: Request,
    db: AsyncSession = Depends(get_db),
    x_razorpay_signature: str = Header(default=""),
):
    body = await request.body()
    service = PaymentService(db)
    await service.handle_webhook("razorpay", body, x_razorpay_signature)
    return {"status": "ok"}


@router.post("/webhook/stripe")
async def stripe_webhook(
    request: Request,
    db: AsyncSession = Depends(get_db),
    stripe_signature: str = Header(default="", alias="Stripe-Signature"),
):
    body = await request.body()
    service = PaymentService(db)
    await service.handle_webhook("stripe", body, stripe_signature)
    return {"status": "ok"}
