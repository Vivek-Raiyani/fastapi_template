"""Auth routes — JSON API and HTML/HTMX pages."""

from fastapi import APIRouter, Depends, Form, Request, Response
from fastapi.responses import RedirectResponse
from sqlalchemy.ext.asyncio import AsyncSession

from core.dependencies import get_db
from core.exceptions import AppError
from core.oauth.google import oauth
from core.settings import settings
from core.templating import is_htmx, template_response
from modules.auth.schemas import (
    ForgotPasswordRequest,
    LoginRequest,
    RefreshRequest,
    RegisterRequest,
    ResetPasswordRequest,
    TokenResponse,
    VerifyEmailRequest,
)
from modules.auth.service import AuthService

router = APIRouter(prefix="/auth", tags=["auth"])

ACCESS_COOKIE = "access_token"


def _set_auth_cookie(response: RedirectResponse, token: str) -> RedirectResponse:
    response.set_cookie(
        key=ACCESS_COOKIE,
        value=token,
        httponly=True,
        samesite="lax",
        max_age=60 * 60 * 24,
    )
    return response


# --- JSON API ---


@router.post("/register", response_model=dict, status_code=201)
async def register(data: RegisterRequest, db: AsyncSession = Depends(get_db)):
    service = AuthService(db)
    user = await service.register(data)
    return {"id": user.id, "email": user.email, "message": "Registration successful"}


@router.post("/refresh", response_model=TokenResponse)
async def refresh_token(data: RefreshRequest, db: AsyncSession = Depends(get_db)):
    service = AuthService(db)
    return await service.refresh(data.refresh_token)


@router.post("/forgot-password", status_code=204)
async def forgot_password(data: ForgotPasswordRequest, db: AsyncSession = Depends(get_db)):
    service = AuthService(db)
    await service.request_password_reset(data.email)


@router.post("/reset-password")
async def reset_password_api(data: ResetPasswordRequest, db: AsyncSession = Depends(get_db)):
    service = AuthService(db)
    user = await service.reset_password(data.token, data.password)
    return {"message": "Password updated", "email": user.email}


@router.post("/verify-email")
async def verify_email_api(data: VerifyEmailRequest, db: AsyncSession = Depends(get_db)):
    service = AuthService(db)
    user = await service.verify_email(data.token)
    return {"message": "Email verified", "email": user.email}


@router.post("/login", response_model=TokenResponse)
async def login_api(data: LoginRequest, db: AsyncSession = Depends(get_db)):
    service = AuthService(db)
    return await service.login(data)


# --- HTML / HTMX ---

html_router = APIRouter(prefix="/auth", tags=["auth-html"])


@html_router.get("/login")
async def login_page(request: Request, error: str | None = None):
    return template_response(
        request,
        "login.html",
        {
            "error": error or request.query_params.get("error"),
            "google_enabled": settings.google_oauth_enabled,
        },
    )


@html_router.get("/register")
async def register_page(request: Request, error: str | None = None):
    return template_response(request, "register.html", {"error": error})


@html_router.post("/login")
async def login_form(
    request: Request,
    response: Response,
    email: str = Form(...),
    password: str = Form(...),
    db: AsyncSession = Depends(get_db),
):
    service = AuthService(db)
    try:
        tokens = await service.login(LoginRequest(email=email, password=password))
    except AppError as exc:
        if is_htmx(request):
            return template_response(
                request,
                "partials/login_form.html",
                {"error": exc.message},
            )
        return template_response(
            request,
            "login.html",
            {"error": exc.message},
        )

    redirect = RedirectResponse(url="/users/profile", status_code=303)
    _set_auth_cookie(redirect, tokens.access_token)
    if is_htmx(request):
        redirect.headers["HX-Redirect"] = "/users/profile"
    return redirect


@html_router.post("/register")
async def register_form(
    request: Request,
    email: str = Form(...),
    password: str = Form(...),
    full_name: str = Form(""),
    db: AsyncSession = Depends(get_db),
):
    service = AuthService(db)
    try:
        await service.register(
            RegisterRequest(email=email, password=password, full_name=full_name or None)
        )
    except AppError as exc:
        if is_htmx(request):
            return template_response(
                request,
                "partials/register_form.html",
                {"error": exc.message},
            )
        return template_response(
            request,
            "register.html",
            {"error": exc.message},
        )

    if is_htmx(request):
        response = RedirectResponse(url="/auth/login", status_code=303)
        response.headers["HX-Redirect"] = "/auth/login"
        return response
    return RedirectResponse(url="/auth/login", status_code=303)


@html_router.get("/verify-email")
async def verify_email_page(token: str, db: AsyncSession = Depends(get_db)):
    service = AuthService(db)
    try:
        await service.verify_email(token)
        return RedirectResponse(url="/auth/login?message=Email+verified", status_code=303)
    except AppError as exc:
        return RedirectResponse(url=f"/auth/login?error={exc.message}", status_code=303)


@html_router.get("/reset-password")
async def reset_password_page(request: Request, token: str):
    from middlewares.csrf import get_csrf_token

    return template_response(
        request, "reset_password.html", {"token": token, "csrf_token": get_csrf_token(request)}
    )


@html_router.post("/reset-password")
async def reset_password_form(
    request: Request,
    token: str = Form(...),
    password: str = Form(...),
    csrf_token: str = Form(""),
    db: AsyncSession = Depends(get_db),
):
    from middlewares.csrf import validate_csrf

    validate_csrf(request, csrf_token)
    service = AuthService(db)
    try:
        await service.reset_password(token, password)
        return RedirectResponse(url="/auth/login?message=Password+updated", status_code=303)
    except AppError as exc:
        return template_response(
            request, "reset_password.html", {"token": token, "error": exc.message}
        )


@html_router.get("/forgot-password")
async def forgot_password_page(request: Request):
    return template_response(request, "forgot_password.html", {})


@html_router.post("/forgot-password")
async def forgot_password_form(
    request: Request,
    email: str = Form(...),
    db: AsyncSession = Depends(get_db),
):
    service = AuthService(db)
    await service.request_password_reset(email)
    return template_response(request, "forgot_password.html", {"sent": True})


@html_router.post("/logout")
async def logout():
    redirect = RedirectResponse(url="/auth/login", status_code=303)
    redirect.delete_cookie(ACCESS_COOKIE)
    return redirect


# --- Google OAuth ---


@html_router.get("/google/login")
async def google_login(request: Request):
    if not settings.google_oauth_enabled:
        return RedirectResponse(
            url="/auth/login?error=Google+OAuth+is+not+configured", status_code=303
        )
    redirect_uri = settings.GOOGLE_REDIRECT_URI
    return await oauth.google.authorize_redirect(request, redirect_uri)


@html_router.get("/google/callback")
async def google_callback(request: Request, db: AsyncSession = Depends(get_db)):
    if not settings.google_oauth_enabled:
        return RedirectResponse(
            url="/auth/login?error=Google+OAuth+is+not+configured", status_code=303
        )

    try:
        token = await oauth.google.authorize_access_token(request)
    except Exception:
        return RedirectResponse(url="/auth/login?error=Google+login+failed", status_code=303)

    userinfo = token.get("userinfo")
    if not userinfo:
        return RedirectResponse(url="/auth/login?error=Google+login+failed", status_code=303)

    service = AuthService(db)
    try:
        _, tokens = await service.google_login_or_register(
            google_id=userinfo["sub"],
            email=userinfo["email"],
            full_name=userinfo.get("name"),
        )
    except AppError:
        return RedirectResponse(url="/auth/login?error=Account+inactive", status_code=303)

    redirect = RedirectResponse(url="/users/profile", status_code=303)
    return _set_auth_cookie(redirect, tokens.access_token)
