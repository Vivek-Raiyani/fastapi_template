"""Role-based access control."""

from enum import Enum

from fastapi import Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from core.dependencies import get_current_user, get_db
from database.models.role import Permission, Role
from database.models.user import User


class PermissionCodename(str, Enum):
    USERS_VIEW = "users.view"
    USERS_EDIT = "users.edit"
    PAYMENTS_VIEW = "payments.view"
    PAYMENTS_CREATE = "payments.create"
    ADMIN_ACCESS = "admin.access"

    # --- BEGIN GENERATED PERMISSIONS ---
    BLOG_CREATE = "blog.create"
    BLOG_READ = "blog.read"
    BLOG_UPDATE = "blog.update"
    BLOG_DELETE = "blog.delete"
    # --- END GENERATED PERMISSIONS ---


async def get_user_permissions(db: AsyncSession, user: User) -> set[str]:
    if user.is_superuser:
        return {p.value for p in PermissionCodename}

    if user.role_id is None:
        return set()

    result = await db.execute(
        select(Role).where(Role.id == user.role_id).options(selectinload(Role.permissions))
    )
    role = result.scalar_one_or_none()
    if role is None:
        return set()
    return {p.codename for p in role.permissions}


def require_permission(codename: str):
    async def checker(
        user: User = Depends(get_current_user),
        db: AsyncSession = Depends(get_db),
    ) -> User:
        perms = await get_user_permissions(db, user)
        if codename not in perms:
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Permission denied")
        return user

    return checker
