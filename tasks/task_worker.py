"""Unified task worker entrypoint."""

import logging
import sys
from typing import Literal

from core.settings import settings

TaskBackend = Literal["apscheduler", "celery", "arq"]


def run_worker(backend: TaskBackend | None = None) -> None:
    backend = backend or settings.TASK_BACKEND
    logging.basicConfig(level=logging.INFO)

    if backend == "apscheduler":
        from tasks.scheduler import run_forever

        run_forever()
    elif backend == "celery":
        from tasks.celery_app import celery_app

        celery_app.worker_main(["worker", "--loglevel=info", *sys.argv[2:]])
    elif backend == "arq":
        import subprocess

        subprocess.run(
            [sys.executable, "-m", "arq", "tasks.arq_worker.WorkerSettings"],
            check=True,
        )
    else:
        raise ValueError(f"Unknown task backend: {backend}")


def run_beat() -> None:
    """Run Celery Beat scheduler (only needed for celery backend)."""
    from tasks.celery_app import celery_app

    celery_app.start(["beat", "--loglevel=info"])
