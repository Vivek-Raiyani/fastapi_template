# Phase 4 — Management CLI

Django-style `manage.py` — one entry point for common operations.

## File

`manage.py` — built with **Typer**

## Commands

### `runserver`

Start the development server (Uvicorn).

```bash
python manage.py runserver
python manage.py runserver --host 0.0.0.0 --port 8080
python manage.py runserver --no-reload
```

Uses `HOST` and `PORT` from settings by default. Reload excludes `venv`, `media`, `__pycache__`, `.git`.

---

### `migrate`

Apply Alembic migrations.

```bash
python manage.py migrate
python manage.py migrate -r 001
```

---

### `makemigrations`

Auto-generate a migration from model changes.

```bash
python manage.py makemigrations -m "add posts table"
```

Always review the generated file in `alembic/versions/` before running `migrate`.

---

### `createsuperuser`

Interactive prompt to create an admin user (`is_superuser=True`).

```bash
python manage.py createsuperuser
```

---

### `shell`

Python REPL with `settings` and `User` pre-imported. Uses IPython if installed.

```bash
python manage.py shell
```

---

### `runworker`

Background task worker — see [Phase 9](./phase-09-background-tasks.md).

```bash
python manage.py runworker                    # uses TASK_BACKEND from .env
python manage.py runworker -b celery          # force Celery
python manage.py runworker -b arq             # force ARQ
python manage.py runworker -b celery --beat   # Celery Beat scheduler
```

## Django comparison

| Django | This template |
|--------|----------------|
| `runserver` | `runserver` |
| `migrate` | `migrate` |
| `makemigrations` | `makemigrations -m "..."` |
| `createsuperuser` | `createsuperuser` |
| `shell` | `shell` |
| `runworker` (Celery) | `runworker -b celery` |

## Status

✅ Complete — all core CLI commands implemented.
