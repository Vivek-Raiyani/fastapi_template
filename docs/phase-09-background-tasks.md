# Phase 9 — Background Tasks

Three task backends — pick the one that fits your deployment. All share the same job definitions in `tasks/jobs.py`.

## Files

| File | Purpose |
|------|---------|
| `tasks/jobs.py` | Shared async job definitions |
| `tasks/scheduler.py` | APScheduler (in-process cron) |
| `tasks/celery_app.py` | Celery app + Beat schedule |
| `tasks/arq_worker.py` | ARQ worker settings |
| `tasks/task_worker.py` | Unified entrypoint |

## Configuration

```env
TASK_BACKEND=apscheduler    # apscheduler | celery | arq
TASK_RUN_IN_APP=false         # run APScheduler inside web process
REDIS_URL=redis://localhost:6379/0
TASK_TIMEZONE=UTC
TASK_HEARTBEAT_MINUTES=30
TASK_CLEANUP_HOUR=3
```

## Backend comparison

| Backend | Redis required | Best for | Command |
|---------|---------------|----------|---------|
| **APScheduler** | No | Dev, small apps, single server | `python manage.py runworker` |
| **Celery** | Yes | Production, distributed, mature ecosystem | `python manage.py runworker -b celery` |
| **ARQ** | Yes | Async-native, lightweight | `python manage.py runworker -b arq` |

## Built-in jobs

Defined in `tasks/jobs.py`:

| Job | Schedule | Description |
|-----|----------|-------------|
| `heartbeat` | Every 30 min | Logs timestamp (health check) |
| `cleanup_inactive_users` | Daily at 03:00 UTC | Removes old inactive OAuth-only users |

## Running workers

### APScheduler (default)

```bash
python manage.py runworker
# or explicitly:
python manage.py runworker -b apscheduler
```

No Redis needed. Runs as a standalone process.

**Optional:** run inside the web app:

```env
TASK_BACKEND=apscheduler
TASK_RUN_IN_APP=true
```

APScheduler starts/stops with Uvicorn lifespan in `main.py`.

### Celery

Requires Redis (`docker compose up redis` or local Redis).

```bash
# Terminal 1 — worker
python manage.py runworker -b celery

# Terminal 2 — scheduler (Beat)
python manage.py runworker -b celery --beat
```

### ARQ

Requires Redis.

```bash
python manage.py runworker -b arq
```

## Adding a new job

### 1. Define the async job

```python
# tasks/jobs.py
async def send_weekly_digest() -> None:
    logger.info("Sending weekly digest...")
    # your logic here
```

### 2. Register per backend

**APScheduler** — `tasks/scheduler.py`:
```python
scheduler.add_job(send_weekly_digest, "cron", day_of_week="mon", hour=9, id="weekly_digest")
```

**Celery** — `tasks/celery_app.py`:
```python
@celery_app.task
def send_weekly_digest_task():
    asyncio.run(send_weekly_digest())

# Add to beat_schedule in celery_app.conf
```

**ARQ** — `tasks/arq_worker.py`:
```python
async def send_weekly_digest_job(_ctx):
    await send_weekly_digest()

# Add to WorkerSettings.functions and cron_jobs
```

## Architecture

```
tasks/jobs.py          ← shared business logic (async)
       ↓
┌──────────────┬──────────────┬──────────────┐
│ APScheduler  │    Celery    │     ARQ      │
│ (in-process) │ (distributed)│ (async Redis)│
└──────────────┴──────────────┴──────────────┘
```

Job logic lives in one place; backends are interchangeable via `TASK_BACKEND`.

## Status

✅ Complete — three backends, example jobs, `manage.py runworker`.
