"""Payment repository."""

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from database.models.payment import Payment


class PaymentRepository:
    def __init__(self, db: AsyncSession):
        self.db = db

    async def get_by_id(self, payment_id: int) -> Payment | None:
        result = await self.db.execute(
            select(Payment).where(Payment.id == payment_id, Payment.deleted_at.is_(None))
        )
        return result.scalar_one_or_none()

    async def get_by_provider_order(self, provider: str, order_id: str) -> Payment | None:
        result = await self.db.execute(
            select(Payment).where(
                Payment.provider == provider,
                Payment.provider_order_id == order_id,
                Payment.deleted_at.is_(None),
            )
        )
        return result.scalar_one_or_none()

    async def create(
        self,
        *,
        user_id: int,
        amount: int,
        currency: str,
        provider: str,
        description: str | None = None,
    ) -> Payment:
        payment = Payment(
            user_id=user_id,
            amount=amount,
            currency=currency,
            provider=provider,
            description=description,
            status="pending",
        )
        self.db.add(payment)
        await self.db.flush()
        await self.db.refresh(payment)
        return payment

    async def update_status(
        self,
        payment: Payment,
        *,
        status: str,
        provider_order_id: str | None = None,
        provider_payment_id: str | None = None,
    ) -> Payment:
        payment.status = status
        if provider_order_id:
            payment.provider_order_id = provider_order_id
        if provider_payment_id:
            payment.provider_payment_id = provider_payment_id
        return payment
