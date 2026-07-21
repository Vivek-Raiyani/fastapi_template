"""S3-compatible storage backend (AWS, MinIO, Cloudflare R2)."""

import aioboto3
from botocore.exceptions import ClientError

from core.settings import settings


class S3Storage:
    def __init__(self):
        if not settings.S3_BUCKET_NAME:
            raise ValueError("S3_BUCKET_NAME is required when STORAGE_BACKEND=s3")

        self.bucket = settings.S3_BUCKET_NAME
        self.public_url = settings.S3_PUBLIC_URL.rstrip("/") if settings.S3_PUBLIC_URL else ""
        self._session = aioboto3.Session()

    def _client_kwargs(self) -> dict:
        kwargs: dict = {"region_name": settings.S3_REGION}
        if settings.S3_ENDPOINT_URL:
            kwargs["endpoint_url"] = settings.S3_ENDPOINT_URL
        return kwargs

    async def save(
        self, key: str, data: bytes, content_type: str = "application/octet-stream"
    ) -> str:
        async with self._session.client(
            "s3",
            aws_access_key_id=settings.S3_ACCESS_KEY_ID or None,
            aws_secret_access_key=settings.S3_SECRET_ACCESS_KEY or None,
            **self._client_kwargs(),
        ) as client:
            await client.put_object(
                Bucket=self.bucket,
                Key=key.lstrip("/"),
                Body=data,
                ContentType=content_type,
            )
        return await self.url(key)

    async def delete(self, key: str) -> None:
        async with self._session.client(
            "s3",
            aws_access_key_id=settings.S3_ACCESS_KEY_ID or None,
            aws_secret_access_key=settings.S3_SECRET_ACCESS_KEY or None,
            **self._client_kwargs(),
        ) as client:
            await client.delete_object(Bucket=self.bucket, Key=key.lstrip("/"))

    async def exists(self, key: str) -> bool:
        async with self._session.client(
            "s3",
            aws_access_key_id=settings.S3_ACCESS_KEY_ID or None,
            aws_secret_access_key=settings.S3_SECRET_ACCESS_KEY or None,
            **self._client_kwargs(),
        ) as client:
            try:
                await client.head_object(Bucket=self.bucket, Key=key.lstrip("/"))
                return True
            except ClientError:
                return False

    async def url(self, key: str, expires: int = 3600) -> str:
        safe_key = key.lstrip("/")
        if self.public_url:
            return f"{self.public_url}/{safe_key}"

        async with self._session.client(
            "s3",
            aws_access_key_id=settings.S3_ACCESS_KEY_ID or None,
            aws_secret_access_key=settings.S3_SECRET_ACCESS_KEY or None,
            **self._client_kwargs(),
        ) as client:
            return await client.generate_presigned_url(
                "get_object",
                Params={"Bucket": self.bucket, "Key": safe_key},
                ExpiresIn=expires,
            )
