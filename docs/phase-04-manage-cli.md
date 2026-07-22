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

---

### `create-module`

Scaffold a new feature module under `modules/`.

```bash
python manage.py create-module blog
python manage.py create-module blog_post
```

Creates `router.py`, `service.py`, `schemas.py`, `repository.py`, and `template/`. Module name must be `snake_case`.

Next step:

```bash
python manage.py generate-crud blog
```

Full details: [Phase 14 — CRUD Generator](./phase-14-crud-generator.md).

---

### `generate-crud`

Generate CRUD code from a SQLAlchemy model in `database/models/{name}.py`.

```bash
python manage.py generate-crud blog
python manage.py generate-crud blog --filters --permissions --tests
```

| Flag | Effect |
|------|--------|
| `--filters` | Search, sort, and field filters on list endpoint |
| `--permissions` | Route guards + auto-register in `core/permissions.py` and `database/seed.py` |
| `--tests` | `tests/test_{name}_crud.py` |

After `--permissions`, run `python manage.py seed-data`. After model changes, re-run the same command to refresh generated code.

Full workflow, review checklist, and architecture: [Phase 14 — CRUD Generator](./phase-14-crud-generator.md).

## Django comparison

| Django | This template |
|--------|----------------|
| `runserver` | `runserver` |
| `migrate` | `migrate` |
| `makemigrations` | `makemigrations -m "..."` |
| `createsuperuser` | `createsuperuser` |
| `shell` | `shell` |
| `runworker` (Celery) | `runworker -b celery` |
| `startapp` | `create-module` |
| Admin + serializers + views | `generate-crud` (see [Phase 14](./phase-14-crud-generator.md)) |

## Status

✅ Complete — core CLI commands plus module scaffolding and CRUD generation.
