"""Database backup with timestamped files and rotation."""

from __future__ import annotations

import asyncio
import shutil
import tempfile
from datetime import UTC, datetime
from pathlib import Path

from sqlalchemy.engine import make_url
from sqlalchemy.ext.asyncio import AsyncSession

from core.settings import BASE_DIR, settings

S3_BACKUP_PREFIX = "db_backups/"


def _s3_client():
    import boto3

    return boto3.client(
        "s3",
        aws_access_key_id=settings.S3_ACCESS_KEY_ID or None,
        aws_secret_access_key=settings.S3_SECRET_ACCESS_KEY or None,
        endpoint_url=settings.S3_ENDPOINT_URL or None,
        region_name=settings.S3_REGION or None,
    )


def _db_path(url) -> Path:
    db_path = Path(url.database or "")
    if not db_path.is_absolute():
        db_path = BASE_DIR / db_path
    return db_path


def _uses_s3() -> bool:
    if settings.STORAGE_BACKEND != "s3":
        return False
    if not settings.S3_BUCKET_NAME:
        raise ValueError("S3_BUCKET_NAME is required when STORAGE_BACKEND=s3")
    return True


def _upload_to_s3(local_path: Path, remote_name: str) -> None:
    s3_key = f"{S3_BACKUP_PREFIX}{remote_name}"
    _s3_client().upload_file(str(local_path), settings.S3_BUCKET_NAME, s3_key)


def _download_from_s3(remote_name: str) -> Path:
    s3_key = f"{S3_BACKUP_PREFIX}{remote_name}"
    tmpfile = tempfile.NamedTemporaryFile(suffix=Path(remote_name).suffix, delete=False)
    tmpfile.close()
    _s3_client().download_file(settings.S3_BUCKET_NAME, s3_key, tmpfile.name)
    return Path(tmpfile.name)


def _rotate_s3_backups() -> None:
    response = _s3_client().list_objects_v2(
        Bucket=settings.S3_BUCKET_NAME,
        Prefix=S3_BACKUP_PREFIX,
    )
    objects = [
        obj
        for obj in response.get("Contents", [])
        if Path(obj["Key"]).name.startswith("backup_")
    ]
    backups = sorted(objects, key=lambda obj: obj["LastModified"])
    while len(backups) > settings.MAX_BACKUPS:
        oldest = backups.pop(0)
        _s3_client().delete_object(Bucket=settings.S3_BUCKET_NAME, Key=oldest["Key"])


def _resolve_backup_path(backup_file: str) -> Path | None:
    path = Path(backup_file)
    if path.is_file():
        return path
    local = settings.BACKUP_DIR / backup_file
    if local.is_file():
        return local
    return None


async def backup(session: AsyncSession) -> None:
    settings.BACKUP_DIR.mkdir(parents=True, exist_ok=True)

    timestamp = datetime.now(UTC).strftime("%Y%m%d_%H%M%S")
    backup_file = settings.BACKUP_DIR / _backup_filename(timestamp)

    await _write_backup(session, backup_file)

    if _uses_s3():
        await asyncio.to_thread(_rotate_s3_backups)
        return

    backups = sorted(
        settings.BACKUP_DIR.glob("backup_*"),
        key=lambda f: f.stat().st_mtime,
    )
    while len(backups) > settings.MAX_BACKUPS:
        oldest = backups.pop(0)
        oldest.unlink(missing_ok=True)


def _backup_filename(timestamp: str) -> str:
    driver = make_url(settings.DATABASE_URL).drivername
    if driver.startswith("sqlite"):
        return f"backup_{timestamp}.sqlite3"
    return f"backup_{timestamp}.sql"


async def _write_backup(session: AsyncSession, backup_file: Path) -> None:
    url = make_url(settings.DATABASE_URL)
    driver = url.drivername
    store_to_s3 = _uses_s3()

    if driver.startswith("sqlite"):
        db_path = _db_path(url)
        if not db_path.is_file():
            raise FileNotFoundError(f"SQLite database file not found: {db_path}")

        if store_to_s3:
            with tempfile.NamedTemporaryFile(suffix=".sqlite3", delete=False) as tmpfile:
                tmpfile_path = Path(tmpfile.name)
            try:
                await asyncio.to_thread(shutil.copy2, db_path, tmpfile_path)
                await asyncio.to_thread(_upload_to_s3, tmpfile_path, backup_file.name)
            finally:
                tmpfile_path.unlink(missing_ok=True)
        else:
            await asyncio.to_thread(shutil.copy2, db_path, backup_file)
        return

    if "postgresql" in driver:
        pg_url = url.set(drivername="postgresql").render_as_string(hide_password=False)
        target_path = backup_file

        if store_to_s3:
            with tempfile.NamedTemporaryFile(suffix=".sql", delete=False) as tmpfile:
                target_path = Path(tmpfile.name)

        proc = await asyncio.create_subprocess_exec(
            "pg_dump",
            pg_url,
            "-f",
            str(target_path),
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
        )
        _, stderr = await proc.communicate()
        if proc.returncode != 0:
            target_path.unlink(missing_ok=True)
            message = stderr.decode().strip() or "pg_dump failed"
            raise RuntimeError(message)

        if store_to_s3:
            try:
                await asyncio.to_thread(_upload_to_s3, target_path, backup_file.name)
            finally:
                target_path.unlink(missing_ok=True)
        return

    raise NotImplementedError(f"Backup not supported for driver: {driver}")


async def restore(backup_file: str) -> None:
    url = make_url(settings.DATABASE_URL)
    driver = url.drivername
    store_to_s3 = settings.STORAGE_BACKEND == "s3"

    source_path = _resolve_backup_path(backup_file)
    temp_path: Path | None = None

    if source_path is None:
        if not store_to_s3:
            raise FileNotFoundError(f"Backup not found: {backup_file}")
        temp_path = await asyncio.to_thread(_download_from_s3, Path(backup_file).name)
        source_path = temp_path

    try:
        if driver.startswith("sqlite"):
            db_path = _db_path(url)
            db_path.parent.mkdir(parents=True, exist_ok=True)
            await asyncio.to_thread(shutil.copy2, source_path, db_path)
            return

        if "postgresql" in driver:
            pg_url = url.set(drivername="postgresql").render_as_string(hide_password=False)
            proc = await asyncio.create_subprocess_exec(
                "psql",
                pg_url,
                "-f",
                str(source_path),
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
            )
            _, stderr = await proc.communicate()
            if proc.returncode != 0:
                message = stderr.decode().strip() or "psql restore failed"
                raise RuntimeError(message)
            return

        raise NotImplementedError(f"Restore not supported for driver: {driver}")
    finally:
        if temp_path is not None:
            temp_path.unlink(missing_ok=True)
