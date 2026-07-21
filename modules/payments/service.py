"""Payment business logic."""

from sqlalchemy.ext.asyncio import AsyncSession

from core.audit import log_audit
from core.exceptions import AppError
from database.models.payment import Payment
from database.models.user import User
from modules.payments.repository import PaymentRepository
from modules.payments.schemas import CreatePaymentRequest
from payments import get_payment_backend


class PaymentService:
    def __init__(self, db: AsyncSession):
        self.db = db
        self.repo = PaymentRepository(db)

    async def create_payment(self, user: User, data: CreatePaymentRequest) -> dict:
        provider = data.provider or "razorpay"
        payment = await self.repo.create(
            user_id=user.id,
            amount=data.amount,
            currency=data.currency.upper(),
            provider=provider,
            description=data.description,
        )
        backend = get_payment_backend(provider)
        order = await backend.create_order(
            amount=data.amount,
            currency=data.currency.upper(),
            receipt=f"payment_{payment.id}",
            notes={"payment_id": str(payment.id), "description": data.description or ""},
        )
        await self.repo.update_status(
            payment, status="pending", provider_order_id=order["order_id"]
        )
        await log_audit(
            self.db,
            action="create",
            model="Payment",
            object_id=payment.id,
            user_id=user.id,
            changes={"amount": data.amount, "provider": provider},
        )
        return {"payment_id": payment.id, **order}

    async def verify_razorpay(
        self,
        user: User,
        *,
        payment_id: int,
        razorpay_order_id: str,
        razorpay_payment_id: str,
        razorpay_signature: str,
    ) -> Payment:
        payment = await self._get_user_payment(user, payment_id)
        backend = get_payment_backend("razorpay")
        result = await backend.verify_payment(
            razorpay_order_id=razorpay_order_id,
            razorpay_payment_id=razorpay_payment_id,
            razorpay_signature=razorpay_signature,
        )
        await self.repo.update_status(
            payment,
            status=result["status"],
            provider_payment_id=result["payment_id"],
        )
        await log_audit(
            self.db, action="paid", model="Payment", object_id=payment.id, user_id=user.id
        )
        return payment

    async def verify_stripe(self, user: User, *, payment_id: int, session_id: str) -> Payment:
        payment = await self._get_user_payment(user, payment_id)
        backend = get_payment_backend("stripe")
        result = await backend.verify_payment(session_id=session_id)
        if result["status"] != "paid":
            raise AppError(f"Payment not completed: {result['status']}", status_code=400)
        await self.repo.update_status(
            payment,
            status="paid",
            provider_payment_id=str(result.get("payment_id")),
        )
        await log_audit(
            self.db, action="paid", model="Payment", object_id=payment.id, user_id=user.id
        )
        return payment

    async def handle_webhook(self, provider: str, body: bytes, signature: str) -> None:
        backend = get_payment_backend(provider)  # type: ignore[arg-type]
        event = backend.verify_webhook(body, signature)

        if provider == "razorpay":
            entity = event.get("payload", {}).get("payment", {}).get("entity", {})
            order_id = entity.get("order_id")
            payment_id_str = entity.get("id")
            if order_id:
                payment = await self.repo.get_by_provider_order("razorpay", order_id)
                if payment:
                    await self.repo.update_status(
                        payment, status="paid", provider_payment_id=payment_id_str
                    )
        elif provider == "stripe":
            if event.get("type") == "checkout.session.completed":
                session = event.get("data", {}).get("object", {})
                order_id = session.get("id")
                if order_id:
                    payment = await self.repo.get_by_provider_order("stripe", order_id)
                    if payment:
                        await self.repo.update_status(
                            payment,
                            status="paid",
                            provider_payment_id=str(session.get("payment_intent")),
                        )

    async def _get_user_payment(self, user: User, payment_id: int) -> Payment:
        payment = await self.repo.get_by_id(payment_id)
        if payment is None:
            raise AppError("Payment not found", status_code=404)
        if payment.user_id != user.id and not user.is_superuser:
            raise AppError("Payment not found", status_code=404)
        return payment
