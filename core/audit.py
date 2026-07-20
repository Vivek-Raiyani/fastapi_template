"""Audit logging utility."""

import json

from sqlalchemy.ext.asyncio import AsyncSession

from database.models.audit_log import AuditLog


async def log_audit(
    db: AsyncSession,
    *,
    action: str,
    model: str,
    object_id: str | int | None = None,
    user_id: int | None = None,
    changes: dict | None = None,
    ip_address: str | None = None,
) -> AuditLog:
    entry = AuditLog(
        user_id=user_id,
        action=action,
        model=model,
        object_id=str(object_id) if object_id is not None else None,
        changes=json.dumps(changes) if changes else None,
        ip_address=ip_address,
    )
    db.add(entry)
    await db.flush()
    return entry
