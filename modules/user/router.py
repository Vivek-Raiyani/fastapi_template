"""User routes — JSON API and HTML pages."""

from fastapi import APIRouter, Depends, Request
from fastapi.responses import RedirectResponse
from sqlalchemy.ext.asyncio import AsyncSession

from core.dependencies import get_current_user, get_current_user_optional, get_db
from core.templating import template_response
from database.models.user import User
from modules.user.schemas import UserRead, UserUpdate
from modules.user.services import UserService

router = APIRouter(prefix="/users", tags=["users"])


@router.get("/me", response_model=UserRead)
async def get_me(current_user: User = Depends(get_current_user)):
    return current_user


@router.patch("/me", response_model=UserRead)
async def update_me(
    data: UserUpdate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    service = UserService(db)
    return await service.update(current_user, data)


# --- HTML routes (HTMX + Jinja2) ---

html_router = APIRouter(prefix="/users", tags=["users-html"])


@html_router.get("/profile")
async def profile_page(
    request: Request,
    db: AsyncSession = Depends(get_db),
    current_user: User | None = Depends(get_current_user_optional),
):
    if current_user is None:
        return RedirectResponse(url="/auth/login", status_code=303)

    return template_response(
        request,
        "profile.html",
        {"user": current_user},
    )
