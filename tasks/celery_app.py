"""Celery app — distributed task queue (requires Redis)."""

import asyncio

from celery import Celery
from celery.schedules import crontab

from core.settings import settings

celery_app = Celery("fastapi_template", broker=settings.REDIS_URL, backend=settings.REDIS_URL)
celery_app.conf.update(
    task_serializer="json",
    result_serializer="json",
    accept_content=["json"],
    timezone=settings.TASK_TIMEZONE,
    enable_utc=True,
    beat_schedule={
        "heartbeat": {
            "task": "tasks.celery_app.heartbeat_task",
            "schedule": settings.TASK_HEARTBEAT_MINUTES * 60.0,
        },
        "cleanup-inactive-users": {
            "task": "tasks.celery_app.cleanup_inactive_users_task",
            "schedule": crontab(hour=settings.TASK_CLEANUP_HOUR, minute=0),
        },
    },
)


def _run_async(coro):
    return asyncio.run(coro)


@celery_app.task(name="tasks.celery_app.heartbeat_task")
def heartbeat_task() -> None:
    from tasks.jobs import heartbeat

    _run_async(heartbeat())


@celery_app.task(name="tasks.celery_app.cleanup_inactive_users_task")
def cleanup_inactive_users_task() -> int:
    from tasks.jobs import cleanup_inactive_users

    return _run_async(cleanup_inactive_users())
