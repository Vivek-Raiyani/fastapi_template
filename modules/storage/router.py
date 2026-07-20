"""File upload routes."""

import uuid
from pathlib import PurePosixPath

from fastapi import APIRouter, Depends, File, UploadFile

from core.dependencies import get_current_user
from database.models.user import User
from storage import get_storage

router = APIRouter(prefix="/storage", tags=["storage"])


def _safe_key(filename: str, user_id: int) -> str:
    suffix = PurePosixPath(filename).suffix.lower()
    return f"uploads/{user_id}/{uuid.uuid4().hex}{suffix}"


@router.post("/upload")
async def upload_file(
    file: UploadFile = File(...),
    current_user: User = Depends(get_current_user),
):
    data = await file.read()
    key = _safe_key(file.filename or "file", current_user.id)
    storage = get_storage()
    url = await storage.save(key, data, content_type=file.content_type or "application/octet-stream")
    return {"key": key, "url": url, "filename": file.filename}
