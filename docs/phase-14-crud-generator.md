# Phase 14 — CRUD Generator

Model-driven code generation for new domain modules. Define a SQLAlchemy model, run one command, and get schemas, repository, service, router, optional filters/permissions/tests, and platform wiring.

See also: [Phase 4 — Management CLI](./phase-04-manage-cli.md) for all `manage.py` commands.

---

## Quick workflow

```bash
# 1. Scaffold the module folder
python manage.py create-module blog

# 2. Define the model
#    database/models/blog.py

# 3. Generate CRUD from the model
python manage.py generate-crud blog
python manage.py generate-crud blog --filters --permissions --tests

# 4. Migrate and seed (when using --permissions)
python manage.py makemigrations -m "add blog"
python manage.py migrate
python manage.py seed-data

# 5. Start the server — router is auto-discovered
python manage.py runserver
```

**Example API** (blog module):

| Method | Path | Auth |
|--------|------|------|
| `GET` | `/api/v1/blogs` | Required |
| `POST` | `/api/v1/blogs` | Required |
| `GET` | `/api/v1/blogs/{id}` | Required |
| `PATCH` | `/api/v1/blogs/{id}` | Required |
| `DELETE` | `/api/v1/blogs/{id}` | Required |

With `--filters`, list supports query params such as:

```text
GET /api/v1/blogs?search=python&is_active=true&sort=created_at&order=desc&page=1&page_size=20
```

---

## Commands

### `create-module`

Creates an empty module skeleton under `modules/{name}/`:

```bash
python manage.py create-module blog
python manage.py create-module blog_post
```

| File | Purpose |
|------|---------|
| `__init__.py` | Package marker |
| `router.py` | Empty `APIRouter` stub |
| `service.py` | Empty service class |
| `schemas.py` | Empty Pydantic stub |
| `repository.py` | Empty repository class |
| `template/` | Optional HTMX templates |

Next step printed by the CLI:

```bash
python manage.py generate-crud blog
```

---

### `generate-crud`

Reads `database/models/{name}.py`, introspects the SQLAlchemy model, and generates CRUD code.

```bash
python manage.py generate-crud blog
python manage.py generate-crud blog --filters
python manage.py generate-crud blog --permissions
python manage.py generate-crud blog --tests
python manage.py generate-crud blog --filters --permissions --tests
```

| Flag | Generates |
|------|-----------|
| *(none)* | Schemas, repository, service, router |
| `--filters` | `filters.py` + search/sort/filter on list endpoint |
| `--permissions` | Permission constants, route guards, platform registration |
| `--tests` | `tests/test_{name}_crud.py` |

**Re-run safe:** After changing the model, run `generate-crud` again. Generated sections are updated; custom code below `# --- END GENERATED ---` is preserved.

---

## Architecture

```
database/models/blog.py          ← source of truth (SQLAlchemy)
        │
        ▼ introspection
modules/blog/
    schemas.py                   ← BlogCreate, BlogUpdate, BlogResponse
    repository.py                ← BlogRepository (extends BaseRepository)
    service.py                   ← BlogService
    router.py                      ← CRUD routes
    filters.py                     ← optional (--filters)
    permissions.py                 ← optional aliases (--permissions)
        │
        ▼
core/registry.py                 ← auto-discovers router (no main.py edit)
```

### Generator package

| File | Role |
|------|------|
| `generators/introspection.py` | Load model, map columns → Pydantic types |
| `generators/crud.py` | Render schemas, repo, service, router, tests |
| `generators/permissions_registry.py` | Update `core/permissions.py` and `database/seed.py` |
| `generators/writers.py` | Marker-based merge for safe regeneration |
| `core/repository.py` | Generic async `BaseRepository` |
| `core/filters.py` | `BaseFilter` (search, sort, order) |

---

## What gets generated

### Schemas (`modules/{name}/schemas.py`)

From model columns:

| Schema | Fields |
|--------|--------|
| `{Model}Create` | Writable columns (excludes `id`, timestamps, `deleted_at`) |
| `{Model}Update` | Same fields, all optional |
| `{Model}Response` | All columns including `id`, timestamps, soft-delete |

**Type mapping examples:**

| SQLAlchemy | Pydantic |
|------------|----------|
| `String(200)` | `str = Field(max_length=200)` |
| `Text` | `str` |
| `Boolean` | `bool` |
| `Integer` | `int` |
| `DateTime` | `datetime` |
| Column name contains `email` | `EmailStr` |

Mixins are detected automatically:

- `TimestampMixin` → `created_at`, `updated_at` in response only
- `SoftDeleteMixin` → soft delete in repository, `deleted_at` in response

### Repository (`modules/{name}/repository.py`)

- Extends `BaseRepository[Model]`
- Respects soft delete (`deleted_at IS NULL`)
- With `--filters`: `apply_filters()` + `list_filtered()` for search/sort/field filters

### Service (`modules/{name}/service.py`)

Thin CRUD layer: `create`, `get`, `list`, `update`, `delete` with commit and 404 handling.

### Router (`modules/{name}/router.py`)

- Prefix from `__tablename__` (e.g. `blogs` → `/blogs`)
- Registered under `API_V1_PREFIX` (`/api/v1`) via `core/registry.py`
- Pagination via `PageParams` and `Page[T]`

**Without `--permissions`:** routes require authentication (`get_current_user`).

**With `--permissions`:** routes require specific codenames via `require_permission()`.

---

## Permissions (`--permissions`)

When `--permissions` is passed, the generator:

1. Creates `modules/{name}/permissions.py` (convenience aliases)
2. Adds entries to `PermissionCodename` in `core/permissions.py`
3. Adds default `user` role grants in `database/seed.py`
4. Protects routes with `require_permission(PermissionCodename.{NAME}_{ACTION}.value)`

### Example: `blog` module

**`core/permissions.py`** (generated block):

```python
class PermissionCodename(str, Enum):
    USERS_VIEW = "users.view"
    # ... hand-written permissions ...

    # --- BEGIN GENERATED PERMISSIONS ---
    BLOG_CREATE = "blog.create"
    BLOG_READ = "blog.read"
    BLOG_UPDATE = "blog.update"
    BLOG_DELETE = "blog.delete"
    # --- END GENERATED PERMISSIONS ---
```

**`database/seed.py`** (generated block — default `user` role):

```python
[
    PermissionCodename.USERS_VIEW.value,
    PermissionCodename.PAYMENTS_VIEW.value,
    PermissionCodename.PAYMENTS_CREATE.value,
    # --- BEGIN GENERATED USER PERMISSIONS ---
    PermissionCodename.BLOG_CREATE.value,
    PermissionCodename.BLOG_READ.value,
    PermissionCodename.BLOG_UPDATE.value,
    PermissionCodename.BLOG_DELETE.value,
    # --- END GENERATED USER PERMISSIONS ---
]
```

**`modules/blog/permissions.py`:**

```python
from core.permissions import PermissionCodename

CREATE = PermissionCodename.BLOG_CREATE
READ = PermissionCodename.BLOG_READ
UPDATE = PermissionCodename.BLOG_UPDATE
DELETE = PermissionCodename.BLOG_DELETE
```

**Router usage:**

```python
from core.permissions import PermissionCodename, require_permission

@router.get("", ...)
async def list_items(..., _user: User = Depends(require_permission(PermissionCodename.BLOG_READ.value))):
    ...
```

### Role defaults

| Role | Generated module permissions |
|------|------------------------------|
| `user` | create, read, update, delete (all four CRUD actions) |
| `admin` | All permissions in `PermissionCodename` (automatic) |
| `superuser` | Bypasses all checks |

After generating with `--permissions`, run:

```bash
python manage.py seed-data
```

### Regenerating permissions

Re-running `generate-crud blog --permissions` updates only that module's entries inside the generated marker blocks. Hand-written permissions (`USERS_VIEW`, `PAYMENTS_CREATE`, etc.) are never touched.

---

## Filters (`--filters`)

Generates `modules/{name}/filters.py`:

```python
class BlogFilter(BaseFilter):
    sort: str | None = None          # default sort: created_at
    order: str = "desc"              # asc | desc (from BaseFilter)
    title: str | None = None
    description: str | None = None
    is_active: bool | None = None
    # datetime fields also get {field}_after / {field}_before
```

List endpoint applies:

- **`search`** — ILIKE across string/text columns
- **Field filters** — exact match on filterable columns
- **`sort` / `order`** — order by column name

Inherited from `BaseFilter`: `search`, `sort`, `order`.

---

## Tests (`--tests`)

Generates `tests/test_{name}_crud.py`:

1. Register + login a test user
2. Create → get → list → update → delete
3. Assert HTTP status codes

With `--permissions`, the test file notes that `seed-data` must be run first.

Run:

```bash
python manage.py seed-data   # if --permissions was used
pytest tests/test_blog_crud.py -v
```

---

## Model registration

`generate-crud` automatically ensures the model is visible to Alembic:

- Adds import to `database/models/__init__.py`
- Adds import to `alembic/env.py`

You still review and run migrations manually:

```bash
python manage.py makemigrations -m "add blog"
python manage.py migrate
```

---

## Custom business logic

Generated files use marker blocks:

```python
# --- BEGIN GENERATED ---
# ... generated CRUD ...
# --- END GENERATED ---

# Add custom routes below.
```

**Safe to edit outside markers:**

- Custom routes in `router.py`
- Custom methods in `service.py` / `repository.py`
- Hand-written permissions in `core/permissions.py` (outside generated block)
- Hand-written seed entries in `database/seed.py` (outside generated block)

**Re-generated on each run:**

- Content between `# --- BEGIN GENERATED ---` and `# --- END GENERATED ---`
- Full `schemas.py`, `filters.py`, `permissions.py`
- Platform permission blocks in `core/permissions.py` and `database/seed.py`

---

## Example: blog module

**Model** — `database/models/blog.py`:

```python
class Blog(Base, TimestampMixin, SoftDeleteMixin):
    __tablename__ = "blogs"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    title: Mapped[str] = mapped_column(String(200), nullable=False)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
```

**Generate:**

```bash
python manage.py create-module blog
python manage.py generate-crud blog --filters --permissions --tests
python manage.py makemigrations -m "add blog"
python manage.py migrate
python manage.py seed-data
```

**Review checklist:**

- [ ] `database/models/blog.py` — model fields correct
- [ ] `modules/blog/schemas.py` — Create/Update/Response match model
- [ ] `modules/blog/router.py` — routes and auth look right
- [ ] `core/permissions.py` — generated BLOG_* entries present
- [ ] `database/seed.py` — user role grants present
- [ ] `alembic/versions/*_add_blog.py` — migration looks correct
- [ ] `tests/test_blog_crud.py` — run with pytest

---

## What the generator does *not* replace

Platform modules remain hand-written:

- `auth` — login, register, OAuth, tokens
- `user` — profile, `/me`
- `payments` — provider integrations, webhooks

Use the generator for **new domain CRUD modules** (posts, products, categories, etc.).

---

## Django comparison

| Django | This template |
|--------|----------------|
| `startapp blog` | `create-module blog` |
| Manual models + admin + serializers + views | `generate-crud blog` from SQLAlchemy model |
| `makemigrations` / `migrate` | Same via `manage.py` |
| Permission classes | `--permissions` + RBAC seed |

---

## Status

✅ Complete — `create-module`, `generate-crud`, filters, permissions auto-registration, tests, safe regeneration.
