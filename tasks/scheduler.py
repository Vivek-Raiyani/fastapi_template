"""APScheduler — in-process async cron (default, no Redis required)."""

import asyncio
import logging

from apscheduler.schedulers.asyncio import AsyncIOScheduler

from core.settings import settings
from tasks.jobs import cleanup_inactive_users, heartbeat

logger = logging.getLogger(__name__)

_scheduler: AsyncIOScheduler | None = None


def get_scheduler() -> AsyncIOScheduler:
    global _scheduler
    if _scheduler is None:
        _scheduler = AsyncIOScheduler(timezone=settings.TASK_TIMEZONE)
    return _scheduler


def register_jobs(scheduler: AsyncIOScheduler) -> None:
    scheduler.add_job(
        heartbeat, "interval", minutes=settings.TASK_HEARTBEAT_MINUTES, id="heartbeat"
    )
    scheduler.add_job(
        cleanup_inactive_users,
        "cron",
        hour=settings.TASK_CLEANUP_HOUR,
        minute=0,
        id="cleanup_inactive_users",
    )


def start_scheduler() -> AsyncIOScheduler:
    scheduler = get_scheduler()
    if not scheduler.running:
        register_jobs(scheduler)
        scheduler.start()
        logger.info("APScheduler started")
    return scheduler


def stop_scheduler() -> None:
    scheduler = get_scheduler()
    if scheduler.running:
        scheduler.shutdown(wait=False)
        logger.info("APScheduler stopped")


def run_forever() -> None:

    logging.basicConfig(level=logging.INFO)

    async def _main() -> None:
        start_scheduler()
        while True:
            await asyncio.sleep(3600)

    try:
        asyncio.run(_main())
    except KeyboardInterrupt:
        stop_scheduler()
