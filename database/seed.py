"""Database seed data — roles, permissions, default admin."""

from sqlalchemy import select

from core.permissions import PermissionCodename
from database.models.role import Permission, Role, role_permissions


async def _link_permissions(session, role: Role, codenames: list[str], perm_map: dict[str, Permission]) -> None:
    for codename in codenames:
        await session.execute(
            role_permissions.insert().values(
                role_id=role.id,
                permission_id=perm_map[codename].id,
            )
        )


async def seed(session) -> None:
    """Seed roles and permissions."""
    perm_map: dict[str, Permission] = {}
    for codename in PermissionCodename:
        result = await session.execute(select(Permission).where(Permission.codename == codename.value))
        perm = result.scalar_one_or_none()
        if perm is None:
            perm = Permission(codename=codename.value, description=codename.name.replace("_", " ").title())
            session.add(perm)
        perm_map[codename.value] = perm
    await session.flush()

    result = await session.execute(select(Role).where(Role.name == "user"))
    user_role = result.scalar_one_or_none()
    if user_role is None:
        user_role = Role(name="user", description="Default authenticated user")
        session.add(user_role)
        await session.flush()
        await _link_permissions(
            session,
            user_role,
            [
                PermissionCodename.USERS_VIEW.value,
                PermissionCodename.PAYMENTS_VIEW.value,
                PermissionCodename.PAYMENTS_CREATE.value,
            ],
            perm_map,
        )

    result = await session.execute(select(Role).where(Role.name == "admin"))
    admin_role = result.scalar_one_or_none()
    if admin_role is None:
        admin_role = Role(name="admin", description="Administrator")
        session.add(admin_role)
        await session.flush()
        await _link_permissions(session, admin_role, list(perm_map.keys()), perm_map)

    await session.commit()
