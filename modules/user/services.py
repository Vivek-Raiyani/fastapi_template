"""User business logic."""

from sqlalchemy.ext.asyncio import AsyncSession

from core.exceptions import AppError
from core.security import hash_password
from database.models.user import User
from modules.user.repository import UserRepository
from modules.user.schemas import UserCreate, UserUpdate


class UserService:
    def __init__(self, db: AsyncSession):
        self.repo = UserRepository(db)

    async def get_by_id(self, user_id: int) -> User:
        user = await self.repo.get_by_id(user_id)
        if user is None:
            raise AppError("User not found", status_code=404)
        return user

    async def create(self, data: UserCreate, *, is_superuser: bool = False) -> User:
        existing = await self.repo.get_by_email(data.email)
        if existing:
            raise AppError("Email already registered", status_code=409)

        return await self.repo.create(
            email=data.email,
            hashed_password=hash_password(data.password),
            full_name=data.full_name,
            is_superuser=is_superuser,
        )

    async def update(self, user: User, data: UserUpdate) -> User:
        if data.full_name is not None:
            user.full_name = data.full_name
        if data.password is not None:
            user.hashed_password = hash_password(data.password)
        return user
