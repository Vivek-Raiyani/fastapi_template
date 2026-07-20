"""Auto-discover and register module routers."""

import importlib
import logging
from pathlib import Path

from fastapi import APIRouter, FastAPI

from core.settings import BASE_DIR, settings

logger = logging.getLogger(__name__)
MODULES_DIR = BASE_DIR / "modules"


def discover_routers() -> list[tuple[APIRouter, str | None, bool]]:
    """
    Discover APIRouter instances from modules/*/router.py.
    Returns list of (router, prefix_override, is_html).
    """
    routers: list[tuple[APIRouter, str | None, bool]] = []

    if not MODULES_DIR.exists():
        return routers

    for module_dir in sorted(MODULES_DIR.iterdir()):
        if not module_dir.is_dir() or module_dir.name.startswith("_"):
            continue
        router_file = module_dir / "router.py"
        if not router_file.exists():
            continue

        module_path = f"modules.{module_dir.name}.router"
        try:
            mod = importlib.import_module(module_path)
        except ImportError as exc:
            logger.warning("Could not import %s: %s", module_path, exc)
            continue

        if hasattr(mod, "router") and isinstance(mod.router, APIRouter):
            routers.append((mod.router, settings.API_V1_PREFIX, False))
            logger.debug("Registered API router: modules.%s.router", module_dir.name)

        if hasattr(mod, "html_router") and isinstance(mod.html_router, APIRouter):
            routers.append((mod.html_router, None, True))
            logger.debug("Registered HTML router: modules.%s.html_router", module_dir.name)

    return routers


def register_routers(app: FastAPI) -> None:
    for router, prefix, is_html in discover_routers():
        if is_html and not settings.SERVE_HTML:
            continue
        if prefix:
            app.include_router(router, prefix=prefix)
        else:
            app.include_router(router)
