"""Storage backend protocol."""

from typing import Protocol


class StorageBackend(Protocol):
    async def save(self, key: str, data: bytes, content_type: str = "application/octet-stream") -> str:
        """Save file and return its public or resolvable URL."""
        ...

    async def delete(self, key: str) -> None:
        """Delete a stored file."""
        ...

    async def exists(self, key: str) -> bool:
        """Check whether a file exists."""
        ...

    async def url(self, key: str, expires: int = 3600) -> str:
        """Return a URL for accessing the file (signed for private buckets)."""
        ...
