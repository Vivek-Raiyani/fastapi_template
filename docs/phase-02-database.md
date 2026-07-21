# Phase 2 — Database

Async SQLAlchemy 2.0 setup — equivalent to Django's ORM layer and `AUTH_USER_MODEL`.

## Files

| File | Purpose |
|------|---------|
| `database/base.py` | `Base` declarative class + `TimestampMixin` |
| `database/db.py` | Async engine, session factory, `get_session()` |
| `database/models/user.py` | User model |
| `database/models/__init__.py` | Model exports (for Alembic autogenerate) |

## Base & mixins

```python
from database.base import Base, TimestampMixin

class MyModel(Base, TimestampMixin):
    __tablename__ = "my_table"
    id: Mapped[int] = mapped_column(primary_key=True)
    # created_at, updated_at added automatically
```

## Session usage

### In FastAPI routes (preferred)

```python
from core.dependencies import get_db
from sqlalchemy.ext.asyncio import AsyncSession

@router.get("/example")
async def example(db: AsyncSession = Depends(get_db)):
    ...
```

### In scripts / CLI

```python
from database.db import async_session_factory

async with async_session_factory() as session:
    # work with session
    await session.commit()
```

## User model

`database/models/user.py` — the template's user table:

| Column | Type | Notes |
|--------|------|-------|
| `id` | int | Primary key |
| `email` | str | Unique, indexed |
| `hashed_password` | str \| null | Null for OAuth-only users |
| `full_name` | str \| null | |
| `is_active` | bool | Default `True` |
| `is_superuser` | bool | Default `False` |
| `google_id` | str \| null | Unique, for Google OAuth |
| `created_at` | datetime | Auto-set |
| `updated_at` | datetime | Auto-updated |

## Database URLs

```env
# Local dev (default)
DATABASE_URL=sqlite+aiosqlite:///./db.sqlite3

# PostgreSQL (Docker Compose or production)
DATABASE_URL=postgresql+asyncpg://postgres:postgres@localhost:5432/app_db
```

Drivers: `aiosqlite` (SQLite), `asyncpg` (PostgreSQL).

## Adding a new model

### Manual workflow

1. Create `database/models/my_model.py`
2. Import it in `database/models/__init__.py`
3. Import in `alembic/env.py` (so autogenerate sees it)
4. Run `python manage.py makemigrations -m "add my_model"`
5. Run `python manage.py migrate`

### CRUD generator workflow (recommended for REST modules)

For standard CRUD APIs, use the generator instead of writing boilerplate by hand:

```bash
python manage.py create-module blog
# edit database/models/blog.py
python manage.py generate-crud blog --filters --permissions --tests
python manage.py makemigrations -m "add blog"
python manage.py migrate
python manage.py seed-data   # when using --permissions
```

See [Phase 14 — CRUD Generator](./phase-14-crud-generator.md) for the full workflow and review checklist.

## Status

✅ Complete — async engine, User model, repository pattern in modules.
