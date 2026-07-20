"""CSRF protection for HTML forms."""

import secrets

from fastapi import HTTPException, Request, status

from middlewares.base import BaseMiddleware

CSRF_SESSION_KEY = "_csrf_token"
CSRF_FORM_FIELD = "csrf_token"
CSRF_HEADER = "X-CSRF-Token"

SAFE_METHODS = {"GET", "HEAD", "OPTIONS", "TRACE"}


def generate_csrf_token() -> str:
    return secrets.token_urlsafe(32)


def get_csrf_token(request: Request) -> str:
    token = request.session.get(CSRF_SESSION_KEY)
    if not token:
        token = generate_csrf_token()
        request.session[CSRF_SESSION_KEY] = token
    return token


def validate_csrf(request: Request, token: str | None) -> None:
    expected = request.session.get(CSRF_SESSION_KEY)
    if not expected or not token or not secrets.compare_digest(expected, token):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="CSRF validation failed")


class CSRFMiddleware(BaseMiddleware):
    """Ensure CSRF token exists in session for HTML routes."""

    async def dispatch(self, request: Request, call_next):
        if request.url.path.startswith("/auth") or request.url.path.startswith("/users"):
            get_csrf_token(request)
        return await call_next(request)
