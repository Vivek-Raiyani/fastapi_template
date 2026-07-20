# Phase 13 — Platform Features

## Implemented

| Feature | Location |
|---------|----------|
| **Refresh token API** | `POST /api/v1/auth/refresh` |
| **Account lockout** | `MAX_LOGIN_ATTEMPTS`, `LOCKOUT_MINUTES` in settings |
| **RBAC** | `database/models/role.py`, `core/permissions.py` |
| **Rate limiting** | `slowapi` — `RATE_LIMIT_DEFAULT=100/minute` |
| **Request logging** | `middlewares/request_logging.py` |
| **Health check** | `GET /health` |
| **Pagination** | `core/pagination.py` — `PageParams`, `paginate()` |
| **Soft delete** | `SoftDeleteMixin` in `database/base.py` |
| **Audit log** | `database/models/audit_log.py`, `core/audit.py` |
| **CSRF** | `middlewares/csrf.py` — HTML form protection |
| **Module auto-discovery** | `core/registry.py` |
| **SQLAdmin** | `core/admin.py` — `/admin` (superuser cookie required) |
| **Seed command** | `python manage.py seed` |
| **Collectstatic** | `python manage.py collectstatic` |
| **Tests** | `tests/` — pytest + httpx |
| **Dockerfile** | Production container image |
| **CI/CD** | `.github/workflows/ci.yml` |

## RBAC

Default roles (via `python manage.py seed`):

| Role | Permissions |
|------|-------------|
| `user` | users.view, payments.view, payments.create |
| `admin` | All permissions |

Superusers bypass all permission checks.

## Admin panel

1. Login as superuser via `/auth/login`
2. Visit `/admin`

## Skipped (per request)

- Pre-commit / lint / format config
- i18n / localization

## Status

✅ Complete
