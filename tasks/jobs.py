"""Example background jobs."""

import logging
from datetime import UTC, datetime, timedelta

from sqlalchemy import delete

from database.db import async_session_factory
from database.models.user import User

logger = logging.getLogger(__name__)


async def heartbeat() -> None:
    """Simple health-check job — logs a timestamp."""
    logger.info("Heartbeat at %s", datetime.now(UTC).isoformat())


async def cleanup_inactive_users(days: int = 365) -> int:
    """
    Example maintenance job — delete inactive non-superuser accounts
    older than `days` with no password (orphaned OAuth stubs).
    """
    cutoff = datetime.now(UTC) - timedelta(days=days)
    async with async_session_factory() as session:
        result = await session.execute(
            delete(User).where(
                User.is_active.is_(False),
                User.is_superuser.is_(False),
                User.hashed_password.is_(None),
                User.created_at < cutoff,
            )
        )
        await session.commit()
        count = result.rowcount or 0
        logger.info("Cleaned up %s inactive OAuth user(s)", count)
        return count
