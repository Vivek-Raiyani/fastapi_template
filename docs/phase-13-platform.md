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
| **Lint & format** | Ruff + pre-commit — see below |
| **Dockerfile** | Production container image |
| **CI/CD** | `.github/workflows/ci.yml` |

## RBAC

Default roles (via `python manage.py seed-data`):

| Role | Permissions |
|------|-------------|
| `user` | users.view, payments.view, payments.create, plus generated module CRUD (see below) |
| `admin` | All permissions |

Superusers bypass all permission checks.

### Generated module permissions

When you run `python manage.py generate-crud {name} --permissions`, the generator:

- Adds `{NAME}_CREATE`, `{NAME}_READ`, `{NAME}_UPDATE`, `{NAME}_DELETE` to `PermissionCodename` in `core/permissions.py`
- Grants all four to the default `user` role in `database/seed.py` (inside generated marker blocks)
- Protects generated routes with `require_permission()`

Then run `python manage.py seed-data` to apply changes to the database.

Details and review checklist: [Phase 14 — CRUD Generator](./phase-14-crud-generator.md).

## Admin panel

1. Login as superuser via `/auth/login`
2. Visit `/admin`

## Lint, format & pre-commit

| File | Purpose |
|------|---------|
| `pyproject.toml` | Ruff lint + format rules |
| `.pre-commit-config.yaml` | Git hooks (runs on every commit) |
| `requirements-dev.txt` | Dev tools: `ruff`, `pre-commit` |

**Setup (once per machine):**

```bash
pip install -r requirements-dev.txt
pre-commit install
```

**Run manually:**

```bash
ruff check .              # lint
ruff check . --fix        # lint + auto-fix
ruff format .             # format
pre-commit run --all-files
```

Pre-commit runs trailing-whitespace, YAML checks, Ruff lint (with fix), and Ruff format before each commit. CI runs the same Ruff checks on every push/PR.

## Skipped (for now)

- i18n / localization

## Status

✅ Complete
