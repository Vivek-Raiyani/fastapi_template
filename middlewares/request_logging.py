"""Request logging middleware."""

import logging
import time

from starlette.requests import Request

from middlewares.base import BaseMiddleware

logger = logging.getLogger("app.request")


class RequestLoggingMiddleware(BaseMiddleware):
    async def dispatch(self, request: Request, call_next):
        start = time.perf_counter()
        response = await call_next(request)
        duration_ms = (time.perf_counter() - start) * 1000
        logger.info(
            "%s %s %s %.1fms",
            request.method,
            request.url.path,
            response.status_code,
            duration_ms,
        )
        return response
