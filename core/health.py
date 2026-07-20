"""Health check and platform routes."""

from fastapi import APIRouter, Depends
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from core.dependencies import get_db
from core.settings import settings

router = APIRouter(tags=["platform"])


@router.get("/health")
async def health(db: AsyncSession = Depends(get_db)):
    db_ok = True
    try:
        await db.execute(text("SELECT 1"))
    except Exception:
        db_ok = False
    status = "ok" if db_ok else "degraded"
    return {
        "status": status,
        "app": settings.APP_NAME,
        "database": "connected" if db_ok else "error",
    }
