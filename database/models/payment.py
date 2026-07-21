"""Payment records."""

from sqlalchemy import ForeignKey, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from database.base import Base, SoftDeleteMixin, TimestampMixin


class Payment(Base, TimestampMixin, SoftDeleteMixin):
    __tablename__ = "payments"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), index=True)
    amount: Mapped[int] = mapped_column(
        Integer, nullable=False
    )  # smallest currency unit (paise/cents)
    currency: Mapped[str] = mapped_column(String(3), default="INR", nullable=False)
    provider: Mapped[str] = mapped_column(String(20), nullable=False)  # razorpay | stripe
    provider_order_id: Mapped[str | None] = mapped_column(String(255), nullable=True, index=True)
    provider_payment_id: Mapped[str | None] = mapped_column(String(255), nullable=True, index=True)
    status: Mapped[str] = mapped_column(String(20), default="pending", nullable=False)
    description: Mapped[str | None] = mapped_column(String(255), nullable=True)
    metadata_json: Mapped[str | None] = mapped_column(Text, nullable=True)
