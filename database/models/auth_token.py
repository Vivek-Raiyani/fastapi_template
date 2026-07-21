"""Auth tokens for email verification and password reset."""

from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, String
from sqlalchemy.orm import Mapped, mapped_column

from database.base import Base, TimestampMixin


class AuthToken(Base, TimestampMixin):
    __tablename__ = "auth_tokens"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), index=True)
    token: Mapped[str] = mapped_column(String(255), unique=True, index=True, nullable=False)
    token_type: Mapped[str] = mapped_column(
        String(50), nullable=False
    )  # verify_email | reset_password
    expires_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    used_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
