"""Auth business logic."""

from datetime import UTC, datetime, timedelta

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from core.audit import log_audit
from core.email import send_template_email
from core.exceptions import AppError
from core.security import (
    create_access_token,
    create_refresh_token,
    hash_password,
    verify_password,
    verify_refresh_token,
)
from core.settings import settings
from database.models.role import Role
from database.models.user import User
from modules.auth.repository import AuthRepository
from modules.auth.schemas import LoginRequest, RegisterRequest, TokenResponse
from modules.auth.token_repository import AuthTokenRepository
from modules.user.schemas import UserCreate
from modules.user.services import UserService


class AuthService:
    def __init__(self, db: AsyncSession):
        self.db = db
        self.repo = AuthRepository(db)
        self.token_repo = AuthTokenRepository(db)
        self.user_service = UserService(db)

    async def register(self, data: RegisterRequest) -> User:
        user = await self.user_service.create(
            UserCreate(email=data.email, password=data.password, full_name=data.full_name)
        )
        await self._assign_default_role(user)
        if settings.REQUIRE_EMAIL_VERIFICATION:
            await self.send_verification_email(user)
        else:
            user.is_verified = True
        await log_audit(self.db, action="register", model="User", object_id=user.id, user_id=user.id)
        return user

    async def login(self, data: LoginRequest) -> TokenResponse:
        user = await self.repo.get_by_email(data.email)
        if user is None or user.hashed_password is None:
            raise AppError("Invalid email or password", status_code=401)

        if user.is_locked:
            raise AppError("Account temporarily locked. Try again later.", status_code=403)

        if not verify_password(data.password, user.hashed_password):
            await self._record_failed_login(user)
            raise AppError("Invalid email or password", status_code=401)

        if settings.REQUIRE_EMAIL_VERIFICATION and not user.is_verified:
            raise AppError("Email not verified", status_code=403)

        if not user.is_active:
            raise AppError("Account is inactive", status_code=403)

        user.failed_login_attempts = 0
        user.locked_until = None
        return self._tokens_for(user)

    async def refresh(self, refresh_token: str) -> TokenResponse:
        user_id = verify_refresh_token(refresh_token)
        if user_id is None:
            raise AppError("Invalid refresh token", status_code=401)
        user = await self.repo.get_by_id(int(user_id))
        if user is None or not user.is_active:
            raise AppError("User not found or inactive", status_code=401)
        return self._tokens_for(user)

    async def send_verification_email(self, user: User) -> None:
        token = await self.token_repo.create(user.id, "verify_email", hours=48)
        link = f"{settings.BASE_URL}/auth/verify-email?token={token.token}"
        await send_template_email(
            to=user.email,
            subject=f"Verify your {settings.APP_NAME} account",
            template="emails/verify_email.html",
            context={"user": user, "link": link},
        )

    async def verify_email(self, token: str) -> User:
        auth_token = await self.token_repo.get_valid(token, "verify_email")
        if auth_token is None:
            raise AppError("Invalid or expired verification link", status_code=400)
        user = await self.repo.get_by_id(auth_token.user_id)
        if user is None:
            raise AppError("User not found", status_code=404)
        user.is_verified = True
        await self.token_repo.mark_used(auth_token)
        await log_audit(self.db, action="verify_email", model="User", object_id=user.id, user_id=user.id)
        return user

    async def request_password_reset(self, email: str) -> None:
        user = await self.repo.get_by_email(email)
        if user is None:
            return  # don't reveal whether email exists
        token = await self.token_repo.create(user.id, "reset_password", hours=2)
        link = f"{settings.BASE_URL}/auth/reset-password?token={token.token}"
        await send_template_email(
            to=user.email,
            subject=f"Reset your {settings.APP_NAME} password",
            template="emails/reset_password.html",
            context={"user": user, "link": link},
        )

    async def reset_password(self, token: str, new_password: str) -> User:
        auth_token = await self.token_repo.get_valid(token, "reset_password")
        if auth_token is None:
            raise AppError("Invalid or expired reset link", status_code=400)
        user = await self.repo.get_by_id(auth_token.user_id)
        if user is None:
            raise AppError("User not found", status_code=404)
        user.hashed_password = hash_password(new_password)
        user.failed_login_attempts = 0
        user.locked_until = None
        await self.token_repo.mark_used(auth_token)
        await log_audit(self.db, action="reset_password", model="User", object_id=user.id, user_id=user.id)
        return user

    async def google_login_or_register(
        self,
        *,
        google_id: str,
        email: str,
        full_name: str | None,
    ) -> tuple[User, TokenResponse]:
        user = await self.repo.get_by_google_id(google_id)
        if user is None:
            user = await self.repo.get_by_email(email)
            if user is None:
                user = await self.repo.create(
                    email=email,
                    full_name=full_name,
                    google_id=google_id,
                )
                user.is_verified = True
                await self._assign_default_role(user)
            elif user.google_id is None:
                user.google_id = google_id
                user.is_verified = True
                if full_name and not user.full_name:
                    user.full_name = full_name

        if not user.is_active:
            raise AppError("Account is inactive", status_code=403)

        return user, self._tokens_for(user)

    async def _record_failed_login(self, user: User) -> None:
        user.failed_login_attempts += 1
        if user.failed_login_attempts >= settings.MAX_LOGIN_ATTEMPTS:
            user.locked_until = datetime.now(UTC) + timedelta(minutes=settings.LOCKOUT_MINUTES)

    async def _assign_default_role(self, user: User) -> None:
        result = await self.db.execute(select(Role).where(Role.name == "user"))
        role = result.scalar_one_or_none()
        if role:
            user.role_id = role.id

    def _tokens_for(self, user: User) -> TokenResponse:
        return TokenResponse(
            access_token=create_access_token(user.id),
            refresh_token=create_refresh_token(user.id),
        )
