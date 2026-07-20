"""FastAPI application factory."""

from contextlib import asynccontextmanager

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from slowapi import Limiter, _rate_limit_exceeded_handler
from slowapi.errors import RateLimitExceeded
from slowapi.middleware import SlowAPIMiddleware
from slowapi.util import get_remote_address
from starlette.middleware.sessions import SessionMiddleware

from core.admin import setup_admin
from core.exceptions import register_exception_handlers
from core.health import router as health_router
from core.logging_config import setup_logging
from core.registry import register_routers
from core.settings import settings
from core.templating import template_response
from middlewares import CSRFMiddleware, RequestLoggingMiddleware

limiter = Limiter(key_func=get_remote_address, default_limits=[settings.RATE_LIMIT_DEFAULT] if settings.RATE_LIMIT_ENABLED else [])


@asynccontextmanager
async def lifespan(app: FastAPI):
    setup_logging(settings.DEBUG)
    settings.MEDIA_ROOT.mkdir(parents=True, exist_ok=True)
    settings.STATIC_ROOT.mkdir(parents=True, exist_ok=True)

    if settings.TASK_BACKEND == "apscheduler" and settings.TASK_RUN_IN_APP:
        from tasks.scheduler import start_scheduler, stop_scheduler

        start_scheduler()
        yield
        stop_scheduler()
    else:
        yield


def create_app() -> FastAPI:
    app = FastAPI(
        title=settings.APP_NAME,
        debug=settings.DEBUG,
        lifespan=lifespan,
    )
    app.state.limiter = limiter

    if settings.RATE_LIMIT_ENABLED:
        app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)
        app.add_middleware(SlowAPIMiddleware)

    app.add_middleware(RequestLoggingMiddleware)
    app.add_middleware(CSRFMiddleware)
    app.add_middleware(SessionMiddleware, secret_key=settings.SECRET_KEY)
    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.CORS_ORIGINS,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    register_exception_handlers(app)
    register_routers(app)
    app.include_router(health_router)

    setup_admin(app)

    if settings.SERVE_HTML:
        @app.get("/")
        async def home(request: Request):
            return template_response(request, "index.html")

        app.mount(
            settings.STATIC_URL.rstrip("/"),
            StaticFiles(directory=str(settings.STATIC_ROOT)),
            name="static",
        )

        if settings.STORAGE_BACKEND == "local":
            app.mount(
                settings.MEDIA_URL.rstrip("/"),
                StaticFiles(directory=str(settings.MEDIA_ROOT)),
                name="media",
            )

    return app


app = create_app()
