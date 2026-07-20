"""Extended features — roles, payments, audit, auth tokens, user fields.

Revision ID: 002
Revises: 001
"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy import inspect

revision: str = "002"
down_revision: Union[str, None] = "001"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def _tables() -> set[str]:
    return set(inspect(op.get_bind()).get_table_names())


def _users_columns() -> set[str]:
    return {c["name"] for c in inspect(op.get_bind()).get_columns("users")}


def upgrade() -> None:
    existing = _tables()

    if "permissions" not in existing:
        op.create_table(
            "permissions",
            sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
            sa.Column("codename", sa.String(100), nullable=False),
            sa.Column("description", sa.String(255), nullable=True),
            sa.PrimaryKeyConstraint("id"),
            sa.UniqueConstraint("codename"),
        )

    if "roles" not in existing:
        op.create_table(
            "roles",
            sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
            sa.Column("name", sa.String(100), nullable=False),
            sa.Column("description", sa.String(255), nullable=True),
            sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("(CURRENT_TIMESTAMP)"), nullable=False),
            sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("(CURRENT_TIMESTAMP)"), nullable=False),
            sa.PrimaryKeyConstraint("id"),
            sa.UniqueConstraint("name"),
        )

    if "role_permissions" not in existing:
        op.create_table(
            "role_permissions",
            sa.Column("role_id", sa.Integer(), nullable=False),
            sa.Column("permission_id", sa.Integer(), nullable=False),
            sa.ForeignKeyConstraint(["permission_id"], ["permissions.id"], ondelete="CASCADE"),
            sa.ForeignKeyConstraint(["role_id"], ["roles.id"], ondelete="CASCADE"),
            sa.PrimaryKeyConstraint("role_id", "permission_id"),
        )

    user_cols = _users_columns()
    if "is_verified" not in user_cols:
        with op.batch_alter_table("users") as batch_op:
            batch_op.add_column(sa.Column("is_verified", sa.Boolean(), server_default=sa.text("0"), nullable=False))
            batch_op.add_column(sa.Column("role_id", sa.Integer(), nullable=True))
            batch_op.add_column(sa.Column("failed_login_attempts", sa.Integer(), server_default="0", nullable=False))
            batch_op.add_column(sa.Column("locked_until", sa.DateTime(timezone=True), nullable=True))
            batch_op.add_column(sa.Column("deleted_at", sa.DateTime(timezone=True), nullable=True))
            batch_op.create_foreign_key("fk_users_role_id", "roles", ["role_id"], ["id"], ondelete="SET NULL")

    if "auth_tokens" not in existing:
        op.create_table(
            "auth_tokens",
            sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
            sa.Column("user_id", sa.Integer(), nullable=False),
            sa.Column("token", sa.String(255), nullable=False),
            sa.Column("token_type", sa.String(50), nullable=False),
            sa.Column("expires_at", sa.DateTime(timezone=True), nullable=False),
            sa.Column("used_at", sa.DateTime(timezone=True), nullable=True),
            sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("(CURRENT_TIMESTAMP)"), nullable=False),
            sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("(CURRENT_TIMESTAMP)"), nullable=False),
            sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
            sa.PrimaryKeyConstraint("id"),
            sa.UniqueConstraint("token"),
        )
        op.create_index("ix_auth_tokens_user_id", "auth_tokens", ["user_id"])
        op.create_index("ix_auth_tokens_token", "auth_tokens", ["token"])

    if "payments" not in existing:
        op.create_table(
            "payments",
            sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
            sa.Column("user_id", sa.Integer(), nullable=False),
            sa.Column("amount", sa.Integer(), nullable=False),
            sa.Column("currency", sa.String(3), nullable=False),
            sa.Column("provider", sa.String(20), nullable=False),
            sa.Column("provider_order_id", sa.String(255), nullable=True),
            sa.Column("provider_payment_id", sa.String(255), nullable=True),
            sa.Column("status", sa.String(20), server_default="pending", nullable=False),
            sa.Column("description", sa.String(255), nullable=True),
            sa.Column("metadata_json", sa.Text(), nullable=True),
            sa.Column("deleted_at", sa.DateTime(timezone=True), nullable=True),
            sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("(CURRENT_TIMESTAMP)"), nullable=False),
            sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("(CURRENT_TIMESTAMP)"), nullable=False),
            sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
            sa.PrimaryKeyConstraint("id"),
        )
        op.create_index("ix_payments_user_id", "payments", ["user_id"])
        op.create_index("ix_payments_provider_order_id", "payments", ["provider_order_id"])

    if "audit_logs" not in existing:
        op.create_table(
            "audit_logs",
            sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
            sa.Column("user_id", sa.Integer(), nullable=True),
            sa.Column("action", sa.String(50), nullable=False),
            sa.Column("model", sa.String(100), nullable=False),
            sa.Column("object_id", sa.String(100), nullable=True),
            sa.Column("changes", sa.Text(), nullable=True),
            sa.Column("ip_address", sa.String(45), nullable=True),
            sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("(CURRENT_TIMESTAMP)"), nullable=False),
            sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("(CURRENT_TIMESTAMP)"), nullable=False),
            sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="SET NULL"),
            sa.PrimaryKeyConstraint("id"),
        )


def downgrade() -> None:
    op.drop_table("audit_logs")
    op.drop_index("ix_payments_provider_order_id", table_name="payments")
    op.drop_index("ix_payments_user_id", table_name="payments")
    op.drop_table("payments")
    op.drop_index("ix_auth_tokens_token", table_name="auth_tokens")
    op.drop_index("ix_auth_tokens_user_id", table_name="auth_tokens")
    op.drop_table("auth_tokens")

    with op.batch_alter_table("users") as batch_op:
        batch_op.drop_constraint("fk_users_role_id", type_="foreignkey")
        batch_op.drop_column("deleted_at")
        batch_op.drop_column("locked_until")
        batch_op.drop_column("failed_login_attempts")
        batch_op.drop_column("role_id")
        batch_op.drop_column("is_verified")

    op.drop_table("role_permissions")
    op.drop_table("roles")
    op.drop_table("permissions")
