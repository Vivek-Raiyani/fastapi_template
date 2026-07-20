"""Jinja2 templating with HTMX helpers."""

from pathlib import Path

from fastapi import Request
from fastapi.templating import Jinja2Templates
from jinja2 import ChoiceLoader, FileSystemLoader

from core.settings import BASE_DIR, settings

# Global templates + per-module templates (modules/*/template/)
_template_dirs: list[Path] = [BASE_DIR / "templates"]

for module_dir in (BASE_DIR / "modules").iterdir():
    if module_dir.is_dir():
        module_template_dir = module_dir / "template"
        if module_template_dir.exists():
            _template_dirs.append(module_template_dir)

templates = Jinja2Templates(
    directory=str(_template_dirs[0]),
    context_processors=[],
)
templates.env.loader = ChoiceLoader([FileSystemLoader(str(d)) for d in _template_dirs])
templates.env.auto_reload = settings.TEMPLATES_AUTO_RELOAD


def is_htmx(request: Request) -> bool:
    """Return True when the request comes from an HTMX element."""
    return request.headers.get("HX-Request") == "true"


def htmx_target(request: Request) -> str | None:
    """Return the HTMX target element id, if any."""
    return request.headers.get("HX-Target")


def template_response(
    request: Request,
    name: str,
    context: dict | None = None,
    *,
    full_page: str | None = None,
):
    """
    Render a template. For HTMX partial requests, render only the fragment;
    for full page loads, wrap in the base layout unless full_page is overridden.
    """
    ctx = {"request": request, "settings": settings, "is_htmx": is_htmx(request)}
    if context:
        ctx.update(context)

    if is_htmx(request) and full_page is None:
        return templates.TemplateResponse(request, name, ctx)

    if full_page:
        ctx["content_template"] = name
        return templates.TemplateResponse(request, full_page, ctx)

    return templates.TemplateResponse(request, name, ctx)
