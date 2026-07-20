"""Storage backends — local filesystem or S3-compatible."""

from storage.factory import get_storage
from storage.local import LocalStorage
from storage.s3 import S3Storage

__all__ = ["LocalStorage", "S3Storage", "get_storage"]
