"""Generic async repository base for CRUD operations."""

from typing import Generic, TypeVar

from sqlalchemy import Select, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from database.base import Base, utcnow

ModelT = TypeVar("ModelT", bound=Base)


class BaseRepository(Generic[ModelT]):
    """Base data-access layer with optional soft-delete support."""

    model: type[ModelT]
    soft_delete: bool = False

    def __init__(self, db: AsyncSession):
        self.db = db

    def _base_query(self) -> Select:
        stmt = select(self.model)
        if self.soft_delete and hasattr(self.model, "deleted_at"):
            stmt = stmt.where(self.model.deleted_at.is_(None))
        return stmt

    async def get_by_id(self, item_id: int) -> ModelT | None:
        result = await self.db.execute(self._base_query().where(self.model.id == item_id))
        return result.scalar_one_or_none()

    async def create(self, **data) -> ModelT:
        instance = self.model(**data)
        self.db.add(instance)
        await self.db.flush()
        await self.db.refresh(instance)
        return instance

    async def update(self, instance: ModelT, **data) -> ModelT:
        for key, value in data.items():
            if value is not None:
                setattr(instance, key, value)
        await self.db.flush()
        await self.db.refresh(instance)
        return instance

    async def delete(self, instance: ModelT) -> None:
        if self.soft_delete and hasattr(instance, "deleted_at"):
            instance.deleted_at = utcnow()
            await self.db.flush()
        else:
            await self.db.delete(instance)
            await self.db.flush()

    async def count(self, stmt: Select | None = None) -> int:
        base = stmt if stmt is not None else self._base_query()
        count_stmt = select(func.count()).select_from(base.subquery())
        return (await self.db.execute(count_stmt)).scalar_one()

    async def list(
        self,
        *,
        skip: int = 0,
        limit: int = 20,
        stmt: Select | None = None,
    ) -> tuple[list[ModelT], int]:
        base = stmt if stmt is not None else self._base_query()
        total = await self.count(base)
        result = await self.db.execute(base.offset(skip).limit(limit))
        return list(result.scalars().all()), total
