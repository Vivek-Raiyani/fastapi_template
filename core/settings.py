"""Application settings loaded from environment variables."""

import json
from functools import lru_cache
from pathlib import Path
from typing import Annotated, Literal

from pydantic import Field, field_validator
from pydantic_settings import BaseSettings, NoDecode, SettingsConfigDict

BASE_DIR = Path(__file__).resolve().parent.parent


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=BASE_DIR / ".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    # App
    APP_NAME: str = "FastAPI Template"
    DEBUG: bool = False
    SECRET_KEY: str = Field(default="change-me-in-production")
    API_V1_PREFIX: str = "/api/v1"
    BASE_URL: str = "http://127.0.0.1:8000"
    BACKUP_DIR: Path = BASE_DIR / "backups"
    MAX_BACKUPS: int = 2

    # Server
    HOST: str = "127.0.0.1"
    PORT: int = 8000

    # Database
    DATABASE_URL: str = Field(default=f"sqlite+aiosqlite:///{BASE_DIR / 'db.sqlite3'}")

    # Auth / JWT
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 60 * 24
    REFRESH_TOKEN_EXPIRE_DAYS: int = 7
    JWT_ALGORITHM: str = "HS256"
    MAX_LOGIN_ATTEMPTS: int = 5
    LOCKOUT_MINUTES: int = 15
    REQUIRE_EMAIL_VERIFICATION: bool = False

    # Google OAuth
    GOOGLE_CLIENT_ID: str = ""
    GOOGLE_CLIENT_SECRET: str = ""
    GOOGLE_REDIRECT_URI: str = "http://127.0.0.1:8000/auth/google/callback"

    # Email
    EMAIL_BACKEND: Literal["console", "smtp"] = "console"
    EMAIL_FROM: str = "noreply@example.com"
    SMTP_HOST: str = "localhost"
    SMTP_PORT: int = 587
    SMTP_USER: str = ""
    SMTP_PASSWORD: str = ""
    SMTP_TLS: bool = True

    # Storage
    STORAGE_BACKEND: Literal["local", "s3"] = "local"
    MEDIA_ROOT: Path = BASE_DIR / "media"
    STATIC_ROOT: Path = BASE_DIR / "statics"
    COLLECTSTATIC_ROOT: Path = BASE_DIR / "static_collected"
    MEDIA_URL: str = "/media/"
    STATIC_URL: str = "/static/"

    # S3
    S3_ENDPOINT_URL: str = ""
    S3_ACCESS_KEY_ID: str = ""
    S3_SECRET_ACCESS_KEY: str = ""
    S3_BUCKET_NAME: str = ""
    S3_REGION: str = "us-east-1"
    S3_PUBLIC_URL: str = ""

    # Payments
    PAYMENT_DEFAULT_PROVIDER: Literal["razorpay", "stripe"] = "razorpay"
    RAZORPAY_KEY_ID: str = ""
    RAZORPAY_KEY_SECRET: str = ""
    RAZORPAY_WEBHOOK_SECRET: str = ""
    STRIPE_SECRET_KEY: str = ""
    STRIPE_PUBLISHABLE_KEY: str = ""
    STRIPE_WEBHOOK_SECRET: str = ""

    # Templates / HTMX
    TEMPLATES_AUTO_RELOAD: bool = True
    SERVE_HTML: bool = True

    # Background tasks
    TASK_BACKEND: Literal["apscheduler", "celery", "arq"] = "apscheduler"
    TASK_RUN_IN_APP: bool = False
    TASK_TIMEZONE: str = "UTC"
    TASK_HEARTBEAT_MINUTES: int = 30
    TASK_CLEANUP_HOUR: int = 3
    REDIS_URL: str = "redis://localhost:6379/0"

    # Rate limiting
    RATE_LIMIT_ENABLED: bool = True
    RATE_LIMIT_DEFAULT: str = "100/minute"

    # Admin
    ADMIN_ENABLED: bool = True
    ADMIN_PATH: str = "/admin"

    # CORS
    CORS_ORIGINS: Annotated[list[str], NoDecode] = [
        "http://localhost:3000",
        "http://127.0.0.1:8000",
    ]

    @field_validator("CORS_ORIGINS", mode="before")
    @classmethod
    def parse_cors_origins(cls, value: str | list[str]) -> list[str]:
        if isinstance(value, list):
            return value
        if not value or not str(value).strip():
            return []
        try:
            parsed = json.loads(value)
        except json.JSONDecodeError:
            return [origin.strip() for origin in value.split(",") if origin.strip()]
        if not isinstance(parsed, list):
            raise ValueError("CORS_ORIGINS must be a comma-separated list or JSON array")
        return parsed

    @property
    def google_oauth_enabled(self) -> bool:
        return bool(self.GOOGLE_CLIENT_ID and self.GOOGLE_CLIENT_SECRET)

    @property
    def razorpay_enabled(self) -> bool:
        return bool(self.RAZORPAY_KEY_ID and self.RAZORPAY_KEY_SECRET)

    @property
    def stripe_enabled(self) -> bool:
        return bool(self.STRIPE_SECRET_KEY)


@lru_cache
def get_settings() -> Settings:
    return Settings()


settings = get_settings()
