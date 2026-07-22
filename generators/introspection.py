"""SQLAlchemy model introspection for code generation."""

from __future__ import annotations

import importlib
import inspect
import re
from dataclasses import dataclass

from sqlalchemy import Boolean, Date, DateTime, Float, Integer, Numeric, String, Text
from sqlalchemy import inspect as sa_inspect
from sqlalchemy.orm import DeclarativeBase

from database.base import Base

AUTO_MANAGED_COLUMNS = frozenset({"id", "created_at", "updated_at", "deleted_at"})
SKIP_CREATE_PATTERNS = ("hashed_password", "password_hash")


@dataclass(frozen=True)
class ColumnMeta:
    name: str
    pydantic_type: str
    pydantic_field: str | None
    nullable: bool
    primary_key: bool
    is_foreign_key: bool
    skip_create: bool
    filterable: bool
    searchable: bool
    sortable: bool


@dataclass(frozen=True)
class ModelMeta:
    module_name: str
    class_name: str
    table_name: str
    route_prefix: str
    model_import: str
    model_class: type
    columns: tuple[ColumnMeta, ...]
    soft_delete: bool
    has_timestamps: bool


def to_class_name(module_name: str) -> str:
    return "".join(part.capitalize() for part in module_name.split("_"))


def to_snake_case(name: str) -> str:
    value = re.sub(r"(?<!^)(?=[A-Z])", "_", name).lower()
    return value.replace("-", "_")


def load_model(module_name: str) -> ModelMeta:
    model_module_path = f"database.models.{module_name}"
    try:
        model_module = importlib.import_module(model_module_path)
    except ModuleNotFoundError as exc:
        raise ValueError(
            f"Model module '{model_module_path}' not found. "
            f"Create database/models/{module_name}.py first."
        ) from exc

    expected_class = to_class_name(module_name)
    model_class = getattr(model_module, expected_class, None)
    if model_class is None:
        model_class = _find_model_class(model_module)
    if model_class is None:
        raise ValueError(
            f"No SQLAlchemy model found in {model_module_path}. "
            f"Expected class '{expected_class}' inheriting from Base."
        )

    mapper = sa_inspect(model_class)
    columns: list[ColumnMeta] = []
    for column in mapper.columns:
        columns.append(_build_column_meta(column))

    table_name = str(mapper.local_table.name)
    soft_delete = "deleted_at" in mapper.columns
    has_timestamps = "created_at" in mapper.columns and "updated_at" in mapper.columns

    return ModelMeta(
        module_name=module_name,
        class_name=model_class.__name__,
        table_name=table_name,
        route_prefix=f"/{table_name}",
        model_import=f"database.models.{module_name}.{model_class.__name__}",
        model_class=model_class,
        columns=tuple(columns),
        soft_delete=soft_delete,
        has_timestamps=has_timestamps,
    )


def _find_model_class(model_module) -> type | None:
    for _, obj in inspect.getmembers(model_module, inspect.isclass):
        if issubclass(obj, Base) and obj is not Base and not _is_mixin(obj):
            return obj
    return None


def _is_mixin(obj: type) -> bool:
    if not issubclass(obj, DeclarativeBase):
        return False
    return obj.__name__.endswith("Mixin")


def _build_column_meta(column) -> ColumnMeta:
    name = column.key
    nullable = bool(column.nullable)
    primary_key = bool(column.primary_key)
    is_foreign_key = bool(column.foreign_keys)
    pydantic_type, pydantic_field = _map_column_type(column, name)
    skip_create = (
        primary_key
        or name in AUTO_MANAGED_COLUMNS
        or any(token in name for token in SKIP_CREATE_PATTERNS)
    )
    filterable = name not in AUTO_MANAGED_COLUMNS and not primary_key
    searchable = filterable and pydantic_type in {"str", "EmailStr"}
    sortable = name in AUTO_MANAGED_COLUMNS or filterable
    return ColumnMeta(
        name=name,
        pydantic_type=pydantic_type,
        pydantic_field=pydantic_field,
        nullable=nullable,
        primary_key=primary_key,
        is_foreign_key=is_foreign_key,
        skip_create=skip_create,
        filterable=filterable,
        searchable=searchable,
        sortable=sortable,
    )


def _map_column_type(column, name: str) -> tuple[str, str | None]:
    if "email" in name.lower():
        return "EmailStr", None

    column_type = column.type
    if isinstance(column_type, Boolean):
        return "bool", None
    if isinstance(column_type, (Integer,)):
        return "int", None
    if isinstance(column_type, (Float, Numeric)):
        return "float", None
    if isinstance(column_type, DateTime):
        return "datetime", None
    if isinstance(column_type, Date):
        return "date", None
    if isinstance(column_type, Text):
        return "str", None
    if isinstance(column_type, String):
        length = getattr(column_type, "length", None)
        if length:
            return "str", f"Field(max_length={length})"
        return "str", None
    return "str", None


def create_fields(meta: ModelMeta) -> list[ColumnMeta]:
    return [col for col in meta.columns if not col.skip_create]


def update_fields(meta: ModelMeta) -> list[ColumnMeta]:
    return [
        col for col in meta.columns if not col.primary_key and col.name not in AUTO_MANAGED_COLUMNS
    ]


def response_fields(meta: ModelMeta) -> list[ColumnMeta]:
    return list(meta.columns)


def filter_fields(meta: ModelMeta) -> list[ColumnMeta]:
    return [col for col in meta.columns if col.filterable]


def default_sort_field(meta: ModelMeta) -> str:
    if meta.has_timestamps:
        return "created_at"
    return "id"


def render_field(col: ColumnMeta, *, required: bool) -> str:
    if col.pydantic_field:
        annotation = col.pydantic_type
        if required and not col.nullable:
            return f"    {col.name}: {annotation} = {col.pydantic_field}"
        return f"    {col.name}: {annotation} | None = {col.pydantic_field}"
    if required and not col.nullable:
        return f"    {col.name}: {col.pydantic_type}"
    return f"    {col.name}: {col.pydantic_type} | None = None"
