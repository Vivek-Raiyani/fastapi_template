# FastAPI Template — Documentation

A Django-inspired FastAPI starter with batteries included: auth, migrations, HTMX/Jinja2, storage, OAuth, background tasks, and Docker Compose.

## Quick start

```bash
copy .env.example .env          # Windows
pip install -r requirements.txt
python manage.py migrate
python manage.py runserver
```

- **Home:** http://127.0.0.1:8000
- **API docs:** http://127.0.0.1:8000/docs
- **Login:** http://127.0.0.1:8000/auth/login

---

## Phase index

| Phase | Topic | Doc |
|-------|--------|-----|
| 1 | Core platform (settings, security, dependencies) | [phase-01-core-platform.md](./phase-01-core-platform.md) |
| 2 | Database (SQLAlchemy async) | [phase-02-database.md](./phase-02-database.md) |
| 3 | Migrations (Alembic) | [phase-03-migrations.md](./phase-03-migrations.md) |
| 4 | Management CLI (`manage.py`) | [phase-04-manage-cli.md](./phase-04-manage-cli.md) |
| 5 | HTMX + Jinja2 (HTML by default) | [phase-05-htmx-jinja.md](./phase-05-htmx-jinja.md) |
| 6 | Auth & User modules | [phase-06-auth-and-user.md](./phase-06-auth-and-user.md) |
| 7 | Storage (local + S3-compatible) | [phase-07-storage.md](./phase-07-storage.md) |
| 8 | Google OAuth | [phase-08-google-oauth.md](./phase-08-google-oauth.md) |
| 9 | Background tasks (APScheduler, Celery, ARQ) | [phase-09-background-tasks.md](./phase-09-background-tasks.md) |
| 10 | Docker Compose (Postgres, MinIO, Redis) | [phase-10-docker-compose.md](./phase-10-docker-compose.md) |
| 11 | Payments (Razorpay + Stripe) | [phase-11-payments.md](./phase-11-payments.md) |
| 12 | Email, password reset, verification | [phase-12-email-auth.md](./phase-12-email-auth.md) |
| 13 | Platform (RBAC, rate limit, admin, tests, CI) | [phase-13-platform.md](./phase-13-platform.md) |
| 14 | CRUD generator (`create-module`, `generate-crud`) | [phase-14-crud-generator.md](./phase-14-crud-generator.md) |

---

## Project layout

```
.
├── alembic/              # DB migration history (Alembic)
├── core/                 # Shared platform code
│   ├── settings.py       # Env-based config (like Django settings.py)
│   ├── security.py       # Password hashing + JWT
│   ├── dependencies.py   # FastAPI deps (get_db, get_current_user)
│   ├── templating.py     # Jinja2 + HTMX helpers
│   └── oauth/            # Google OAuth (Authlib)
├── database/             # SQLAlchemy base, session, models
├── generators/           # CRUD code generation (introspection, writers)
├── modules/              # Feature modules (like Django apps)
│   ├── auth/             # Register, login, OAuth
│   ├── user/             # Profile, /me API
│   ├── storage/          # File upload API
│   └── blog/             # Example generated CRUD module
├── storage/              # Storage backends (local, S3)
├── tasks/                # Background jobs (3 backends)
├── templates/            # Global Jinja2 templates
├── statics/              # CSS, JS, images
├── media/                # Local uploads (when STORAGE_BACKEND=local)
├── main.py               # FastAPI app factory
├── manage.py             # CLI (migrate, runserver, runworker, …)
├── docker-compose.yml    # Postgres + Redis + MinIO
└── .env.example          # All configurable settings
```

---

## Django → FastAPI mapping

| Django | This template |
|--------|----------------|
| `settings.py` | `core/settings.py` |
| `manage.py` | `manage.py` |
| `startapp` + manual CRUD | `create-module` + `generate-crud` |
| `apps/` | `modules/` |
| `models.py` | `database/models/` |
| `migrations/` | `alembic/versions/` |
| `urls.py` | `modules/*/router.py` |
| `AUTH_USER_MODEL` | `database/models/user.py` |
| `django.contrib.staticfiles` | `statics/` + FastAPI `StaticFiles` |
| `MEDIA_ROOT` | `media/` + `storage/` backends |
| `django-allauth` (Google) | `core/oauth/google.py` |
| Celery / crontab | `tasks/` (APScheduler, Celery, ARQ) |

---

## Environment variables

See `.env.example` for the full list. Key groups:

- **App:** `APP_NAME`, `DEBUG`, `SECRET_KEY`
- **Database:** `DATABASE_URL`
- **Auth:** `ACCESS_TOKEN_EXPIRE_MINUTES`, Google OAuth vars
- **Storage:** `STORAGE_BACKEND`, S3 vars
- **Tasks:** `TASK_BACKEND`, `REDIS_URL`
- **HTML:** `SERVE_HTML`, `TEMPLATES_AUTO_RELOAD`
