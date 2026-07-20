"""Base class for application middleware."""

from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import Response


class BaseMiddleware(BaseHTTPMiddleware):
    """Extend this to add custom request/response middleware."""

    async def dispatch(self, request: Request, call_next) -> Response:
        return await call_next(request)
