"""Pagination helpers."""

from typing import Generic, TypeVar

from pydantic import BaseModel, Field
from sqlalchemy import Select, func, select
from sqlalchemy.ext.asyncio import AsyncSession

T = TypeVar("T")


class PageParams(BaseModel):
    page: int = Field(1, ge=1)
    page_size: int = Field(20, ge=1, le=100)

    @property
    def offset(self) -> int:
        return (self.page - 1) * self.page_size


class Page(BaseModel, Generic[T]):
    items: list[T]
    total: int
    page: int
    page_size: int
    pages: int


async def paginate(
    db: AsyncSession,
    stmt: Select,
    params: PageParams,
    *,
    scalars: bool = True,
) -> tuple[list, int]:
    count_stmt = select(func.count()).select_from(stmt.subquery())
    total = (await db.execute(count_stmt)).scalar_one()
    paginated = stmt.offset(params.offset).limit(params.page_size)
    result = await db.execute(paginated)
    items = list(result.scalars().all()) if scalars else list(result.all())
    return items, total


def build_page(items: list[T], total: int, params: PageParams) -> Page[T]:
    pages = max(1, (total + params.page_size - 1) // params.page_size)
    return Page(items=items, total=total, page=params.page, page_size=params.page_size, pages=pages)
