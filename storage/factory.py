"""Storage backend factory."""

from functools import lru_cache

from core.settings import settings
from storage.base import StorageBackend
from storage.local import LocalStorage
from storage.s3 import S3Storage


@lru_cache
def get_storage() -> StorageBackend:
    if settings.STORAGE_BACKEND == "s3":
        return S3Storage()
    return LocalStorage()
