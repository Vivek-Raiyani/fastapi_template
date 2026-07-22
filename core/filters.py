"""Shared filter helpers for list endpoints."""

from typing import Literal

from pydantic import BaseModel, Field


class BaseFilter(BaseModel):
    """Common list query parameters."""

    search: str | None = None
    sort: str | None = None
    order: Literal["asc", "desc"] = Field(default="desc")
