# Phase 1 — Core Platform

The foundation layer — equivalent to Django's `settings.py`, auth utilities, and shared dependencies.

## Files

| File | Purpose |
|------|---------|
| `core/settings.py` | All configuration from environment variables |
| `core/security.py` | bcrypt password hashing, JWT create/verify |
| `core/dependencies.py` | `get_db`, `get_current_user`, cookie + Bearer auth |
| `core/exceptions.py` | `AppError` + JSON exception handler |
| `.env.example` | Documented defaults for every setting |

## Settings (`core/settings.py`)

Loaded via **Pydantic Settings** from `.env`:

```python
from core.settings import settings

settings.APP_NAME
settings.DATABASE_URL
settings.STORAGE_BACKEND   # "local" | "s3"
settings.TASK_BACKEND      # "apscheduler" | "celery" | "arq"
settings.google_oauth_enabled  # True when Google creds are set
```

### Important defaults

| Setting | Default | Notes |
|---------|---------|-------|
| `DATABASE_URL` | SQLite (`db.sqlite3`) | Switch to Postgres in production |
| `API_V1_PREFIX` | `/api/v1` | All JSON API routes prefixed |
| `SECRET_KEY` | `change-me-in-production` | Used for JWT + sessions |
| `CORS_ORIGINS` | localhost origins | Comma-separated or JSON array in `.env` |

### CORS parsing

`CORS_ORIGINS` accepts either format in `.env`:

```env
CORS_ORIGINS=http://localhost:3000,http://127.0.0.1:8000
# or
CORS_ORIGINS=["http://localhost:3000","http://127.0.0.1:8000"]
```

## Security (`core/security.py`)

```python
from core.security import hash_password, verify_password, create_access_token

hashed = hash_password("secret")
verify_password("secret", hashed)  # True

token = create_access_token(user_id=1)
```

- **Passwords:** bcrypt (direct, not passlib)
- **Tokens:** JWT via `python-jose` — access + refresh token types

## Dependencies (`core/dependencies.py`)

Used in route handlers via FastAPI `Depends()`:

| Dependency | Description |
|------------|-------------|
| `get_db()` | Async SQLAlchemy session (auto-commit/rollback) |
| `get_current_user()` | Requires valid JWT (Bearer header **or** `access_token` cookie) |
| `get_current_user_optional()` | Same but returns `None` if unauthenticated |
| `get_current_superuser()` | Requires `is_superuser=True` |

### Dual auth mode

- **JSON API:** `Authorization: Bearer <token>`
- **HTML pages:** `access_token` HTTP-only cookie set on login

## Exceptions

Raise `AppError` in services for consistent API errors:

```python
from core.exceptions import AppError

raise AppError("Email already registered", status_code=409)
```

Returns JSON: `{"detail": "Email already registered"}`

## Status

✅ Complete — settings, security, dependencies, and exceptions are wired into `main.py` and all modules.
