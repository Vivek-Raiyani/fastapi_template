"""Auth token repository."""

import secrets
from datetime import UTC, datetime, timedelta

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from database.models.auth_token import AuthToken


class AuthTokenRepository:
    def __init__(self, db: AsyncSession):
        self.db = db

    async def create(self, user_id: int, token_type: str, hours: int = 24) -> AuthToken:
        token = AuthToken(
            user_id=user_id,
            token=secrets.token_urlsafe(32),
            token_type=token_type,
            expires_at=datetime.now(UTC) + timedelta(hours=hours),
        )
        self.db.add(token)
        await self.db.flush()
        await self.db.refresh(token)
        return token

    async def get_valid(self, token: str, token_type: str) -> AuthToken | None:
        result = await self.db.execute(
            select(AuthToken).where(
                AuthToken.token == token,
                AuthToken.token_type == token_type,
                AuthToken.used_at.is_(None),
                AuthToken.expires_at > datetime.now(UTC),
            )
        )
        return result.scalar_one_or_none()

    async def mark_used(self, auth_token: AuthToken) -> None:
        auth_token.used_at = datetime.now(UTC)
