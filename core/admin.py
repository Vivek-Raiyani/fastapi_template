"""SQLAdmin setup."""

from sqladmin import Admin, ModelView
from sqladmin.authentication import AuthenticationBackend
from starlette.requests import Request

from core.dependencies import ACCESS_COOKIE
from core.security import verify_access_token
from core.settings import settings
from database.db import engine
from database.models.audit_log import AuditLog
from database.models.payment import Payment
from database.models.role import Permission, Role
from database.models.user import User


class AdminAuth(AuthenticationBackend):
    async def login(self, request: Request) -> bool:
        return False

    async def logout(self, request: Request) -> bool:
        return True

    async def authenticate(self, request: Request) -> bool:
        token = request.cookies.get(ACCESS_COOKIE)
        if not token:
            return False
        user_id = verify_access_token(token)
        if not user_id:
            return False
        from database.db import async_session_factory
        from modules.user.repository import UserRepository

        async with async_session_factory() as session:
            user = await UserRepository(session).get_by_id(int(user_id))
            if user is None or not user.is_superuser:
                return False
        return True


class UserAdmin(ModelView, model=User):
    column_list = [
        User.id,
        User.email,
        User.full_name,
        User.is_active,
        User.is_superuser,
        User.is_verified,
    ]
    column_searchable_list = [User.email, User.full_name]
    form_excluded_columns = [User.hashed_password]


class RoleAdmin(ModelView, model=Role):
    column_list = [Role.id, Role.name, Role.description]


class PermissionAdmin(ModelView, model=Permission):
    column_list = [Permission.id, Permission.codename, Permission.description]


class PaymentAdmin(ModelView, model=Payment):
    column_list = [
        Payment.id,
        Payment.user_id,
        Payment.amount,
        Payment.currency,
        Payment.provider,
        Payment.status,
    ]


class AuditLogAdmin(ModelView, model=AuditLog):
    column_list = [
        AuditLog.id,
        AuditLog.action,
        AuditLog.model,
        AuditLog.object_id,
        AuditLog.user_id,
        AuditLog.created_at,
    ]
    can_create = False
    can_edit = False
    can_delete = False


def setup_admin(app) -> Admin | None:
    if not settings.ADMIN_ENABLED:
        return None
    admin = Admin(
        app,
        engine,
        authentication_backend=AdminAuth(secret_key=settings.SECRET_KEY),
        base_url=settings.ADMIN_PATH,
    )
    admin.add_view(UserAdmin)
    admin.add_view(RoleAdmin)
    admin.add_view(PermissionAdmin)
    admin.add_view(PaymentAdmin)
    admin.add_view(AuditLogAdmin)
    return admin
