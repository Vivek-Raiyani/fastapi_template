# Phase 5 — HTMX + Jinja2

Server-rendered HTML by default, with HTMX for partial page updates — no separate frontend required.

## Files

| File | Purpose |
|------|---------|
| `core/templating.py` | Jinja2 setup, HTMX helpers, `template_response()` |
| `templates/base.html` | Root layout — loads HTMX CDN + app CSS |
| `templates/index.html` | Home page |
| `modules/*/template/` | Per-module templates (auto-discovered) |
| `statics/css/app.css` | Base styles |

## Template loading

Jinja2 searches **two** directories via `ChoiceLoader`:

1. `templates/` — shared layouts (`base.html`, `index.html`)
2. `modules/*/template/` — module-specific pages (`auth/login.html`, `user/profile.html`)

Module templates use `{% extends "base.html" %}` like normal Jinja inheritance.

## HTMX helpers

```python
from core.templating import template_response, is_htmx

@router.get("/page")
async def page(request: Request):
    return template_response(request, "my_page.html", {"data": value})
```

- `is_htmx(request)` — `True` when `HX-Request: true` header is present
- `template_response()` — renders template with `request`, `settings`, `is_htmx` in context

## HTMX patterns in auth

Login form (`modules/auth/template/partials/login_form.html`):

```html
<form
    hx-post="/auth/login"
    hx-target="#auth-form-container"
    hx-swap="innerHTML"
>
```

- **Success:** server returns `HX-Redirect` header → browser navigates to profile
- **Error:** server returns partial HTML → only the form area updates

## Dual route pattern

Each feature module can expose two routers:

```python
router       # JSON API  → /api/v1/...
html_router  # HTML pages → /auth/..., /users/...
```

Registered separately in `main.py`.

## Toggle HTML serving

```env
SERVE_HTML=true   # mount HTML routes, static, media
SERVE_HTML=false  # API-only mode
```

## Static files

| Path | Served at | When |
|------|-----------|------|
| `statics/` | `/static/` | Always (when `SERVE_HTML=true`) |
| `media/` | `/media/` | When `STORAGE_BACKEND=local` |

HTMX is loaded from CDN in `base.html`. To self-host, add `statics/js/htmx.min.js` and update the script tag.

## Adding a new HTML page

1. Create `modules/myfeature/template/page.html` extending `base.html`
2. Add route to `modules/myfeature/router.py`:

```python
html_router = APIRouter(prefix="/myfeature")

@html_router.get("/page")
async def my_page(request: Request):
    return template_response(request, "page.html", {"key": "value"})
```

3. Register `html_router` in `main.py`

## Status

✅ Complete — base layout, HTMX forms, module template discovery, static serving.
