"""Auth repository."""

from sqlalchemy.ext.asyncio import AsyncSession

from modules.user.repository import UserRepository


class AuthRepository(UserRepository):
    """Auth-specific queries — extends UserRepository."""

    def __init__(self, db: AsyncSession):
        super().__init__(db)
