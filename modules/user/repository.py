"""User repository — database access layer."""

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from database.models.user import User


def _active_users():
    return select(User).where(User.deleted_at.is_(None))


class UserRepository:
    def __init__(self, db: AsyncSession):
        self.db = db

    async def get_by_id(self, user_id: int) -> User | None:
        result = await self.db.execute(_active_users().where(User.id == user_id))
        return result.scalar_one_or_none()

    async def get_by_email(self, email: str) -> User | None:
        result = await self.db.execute(_active_users().where(User.email == email))
        return result.scalar_one_or_none()

    async def get_by_google_id(self, google_id: str) -> User | None:
        result = await self.db.execute(_active_users().where(User.google_id == google_id))
        return result.scalar_one_or_none()

    async def create(
        self,
        *,
        email: str,
        hashed_password: str | None = None,
        full_name: str | None = None,
        google_id: str | None = None,
        is_superuser: bool = False,
    ) -> User:
        user = User(
            email=email,
            hashed_password=hashed_password,
            full_name=full_name,
            google_id=google_id,
            is_superuser=is_superuser,
        )
        self.db.add(user)
        await self.db.flush()
        await self.db.refresh(user)
        return user

    async def list_all(self, skip: int = 0, limit: int = 100) -> list[User]:
        result = await self.db.execute(_active_users().offset(skip).limit(limit))
        return list(result.scalars().all())
