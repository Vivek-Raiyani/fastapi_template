"""ARQ worker — async-native Redis queue."""

import logging
from datetime import timedelta

from arq import cron
from arq.connections import RedisSettings

from core.settings import settings
from tasks.jobs import cleanup_inactive_users, heartbeat

logger = logging.getLogger(__name__)


async def heartbeat_job(_ctx) -> None:
    await heartbeat()


async def cleanup_inactive_users_job(_ctx) -> int:
    return await cleanup_inactive_users()


async def startup(_ctx) -> None:
    logger.info("ARQ worker started")


async def shutdown(_ctx) -> None:
    logger.info("ARQ worker stopped")


class WorkerSettings:
    redis_settings = RedisSettings.from_dsn(settings.REDIS_URL)
    functions = [heartbeat_job, cleanup_inactive_users_job]
    cron_jobs = [
        cron(heartbeat_job, minute={0, 30}),
        cron(cleanup_inactive_users_job, hour=settings.TASK_CLEANUP_HOUR, minute=0),
    ]
    on_startup = startup
    on_shutdown = shutdown
    job_timeout = timedelta(minutes=10)
