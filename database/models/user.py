"""User model — equivalent to Django's AUTH_USER_MODEL."""

from datetime import UTC, datetime

from sqlalchemy import Boolean, DateTime, ForeignKey, Integer, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from database.base import Base, SoftDeleteMixin, TimestampMixin


class User(Base, TimestampMixin, SoftDeleteMixin):
    __tablename__ = "users"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    email: Mapped[str] = mapped_column(String(255), unique=True, index=True, nullable=False)
    hashed_password: Mapped[str | None] = mapped_column(String(255), nullable=True)
    full_name: Mapped[str | None] = mapped_column(String(255), nullable=True)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    is_superuser: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    is_verified: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)

    # OAuth
    google_id: Mapped[str | None] = mapped_column(String(255), unique=True, nullable=True)

    # RBAC
    role_id: Mapped[int | None] = mapped_column(
        ForeignKey("roles.id", ondelete="SET NULL"), nullable=True
    )

    # Account lockout
    failed_login_attempts: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    locked_until: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    role = relationship("Role", lazy="selectin")

    @property
    def is_oauth_user(self) -> bool:
        return self.google_id is not None and self.hashed_password is None

    @property
    def is_locked(self) -> bool:
        if self.locked_until is None:
            return False
        lock = self.locked_until
        if lock.tzinfo is None:
            lock = lock.replace(tzinfo=UTC)
        return lock > datetime.now(UTC)
