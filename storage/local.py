"""Local filesystem storage backend."""

from pathlib import Path

import aiofiles

from core.settings import settings


class LocalStorage:
    def __init__(self, root: Path | None = None, base_url: str | None = None):
        self.root = root or settings.MEDIA_ROOT
        self.base_url = (base_url or settings.MEDIA_URL).rstrip("/")

    def _path(self, key: str) -> Path:
        safe_key = key.lstrip("/").replace("..", "")
        path = self.root / safe_key
        path.parent.mkdir(parents=True, exist_ok=True)
        return path

    async def save(
        self, key: str, data: bytes, content_type: str = "application/octet-stream"
    ) -> str:
        path = self._path(key)
        async with aiofiles.open(path, "wb") as f:
            await f.write(data)
        return f"{self.base_url}/{key.lstrip('/')}"

    async def delete(self, key: str) -> None:
        path = self._path(key)
        if path.exists():
            path.unlink()

    async def exists(self, key: str) -> bool:
        return self._path(key).exists()

    async def url(self, key: str, expires: int = 3600) -> str:
        return f"{self.base_url}/{key.lstrip('/')}"
