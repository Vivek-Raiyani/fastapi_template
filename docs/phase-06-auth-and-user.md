# Phase 6 — Auth & User Modules

Feature modules following the layered pattern: **router → service → repository → model**.

## Module structure

```
modules/auth/
├── router.py       # API + HTML routes
├── service.py      # Business logic
├── repository.py   # DB queries (extends UserRepository)
├── schemas.py      # Pydantic request/response models
└── template/       # Login, register HTML

modules/user/
├── router.py
├── services.py
├── repository.py
├── schemas.py
└── template/       # Profile page
```

## Auth — JSON API

| Method | Path | Description |
|--------|------|-------------|
| `POST` | `/api/v1/auth/register` | Register with email + password |
| `POST` | `/api/v1/auth/login` | Returns JWT access + refresh tokens |

### Example

```bash
# Register
curl -X POST http://127.0.0.1:8000/api/v1/auth/register \
  -H "Content-Type: application/json" \
  -d '{"email":"user@example.com","password":"password123","full_name":"User"}'

# Login
curl -X POST http://127.0.0.1:8000/api/v1/auth/login \
  -H "Content-Type: application/json" \
  -d '{"email":"user@example.com","password":"password123"}'
```

Response:
```json
{
  "access_token": "eyJ...",
  "refresh_token": "eyJ...",
  "token_type": "bearer"
}
```

## Auth — HTML routes

| Method | Path | Description |
|--------|------|-------------|
| `GET` | `/auth/login` | Login page |
| `GET` | `/auth/register` | Register page |
| `POST` | `/auth/login` | Form login → sets cookie → redirect |
| `POST` | `/auth/register` | Form register → redirect to login |
| `POST` | `/auth/logout` | Clears cookie |

## User — JSON API

| Method | Path | Auth | Description |
|--------|------|------|-------------|
| `GET` | `/api/v1/users/me` | Required | Current user profile |
| `PATCH` | `/api/v1/users/me` | Required | Update name/password |

```bash
curl http://127.0.0.1:8000/api/v1/users/me \
  -H "Authorization: Bearer <access_token>"
```

## User — HTML

| Method | Path | Description |
|--------|------|-------------|
| `GET` | `/users/profile` | Profile page (redirects to login if unauthenticated) |

## Layer responsibilities

| Layer | Does | Does not |
|-------|------|----------|
| **router** | HTTP, forms, redirects, cookies | Business rules |
| **service** | Validation, orchestration, `AppError` | Raw SQL |
| **repository** | Database queries | HTTP concerns |
| **schemas** | Request/response shapes | Logic |

## Adding a new module

1. Create `modules/myapp/` with `router.py`, `service.py`, `repository.py`, `schemas.py`
2. Add SQLAlchemy models in `database/models/`
3. Create migration: `python manage.py makemigrations -m "add myapp"`
4. Register routers in `main.py`:

```python
from modules.myapp.router import router as myapp_router
app.include_router(myapp_router, prefix=settings.API_V1_PREFIX)
```

## Status

✅ Complete — register, login (API + HTML), profile, JWT + cookie auth.
