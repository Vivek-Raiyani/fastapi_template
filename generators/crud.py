"""Generate CRUD module files from a SQLAlchemy model."""

from __future__ import annotations

from pathlib import Path

from generators.introspection import (
    ModelMeta,
    create_fields,
    default_sort_field,
    filter_fields,
    load_model,
    render_field,
    response_fields,
    update_fields,
)
from generators.permissions_registry import enum_member, enum_prefix, register_module_permissions
from generators.writers import merge_generated_content, write_file

ROOT = Path(__file__).resolve().parent.parent


def generate_crud(
    module_name: str,
    *,
    with_filters: bool = False,
    with_permissions: bool = False,
    with_tests: bool = False,
) -> list[str]:
    """Generate CRUD files for a module. Returns list of created/updated paths."""
    meta = load_model(module_name)
    module_dir = ROOT / "modules" / module_name
    if not module_dir.exists():
        raise ValueError(
            f"Module '{module_name}' not found at modules/{module_name}/. "
            f"Run: python manage.py create-module {module_name}"
        )

    written: list[str] = []

    _ensure_model_registered(meta)
    written.extend(_registration_notes(meta))

    schemas_path = module_dir / "schemas.py"
    write_file(schemas_path, _render_schemas(meta))
    written.append(str(schemas_path.relative_to(ROOT)))

    repository_path = module_dir / "repository.py"
    existing_repo = (
        repository_path.read_text(encoding="utf-8") if repository_path.exists() else None
    )
    write_file(
        repository_path,
        merge_generated_content(
            existing_repo,
            header=_repository_header(meta, with_filters=with_filters),
            body=_render_repository_body(meta, with_filters=with_filters),
            footer="# Add custom repository methods below.",
        ),
    )
    written.append(str(repository_path.relative_to(ROOT)))

    service_path = module_dir / "service.py"
    existing_service = service_path.read_text(encoding="utf-8") if service_path.exists() else None
    write_file(
        service_path,
        merge_generated_content(
            existing_service,
            header=_service_header(meta, with_filters=with_filters),
            body=_render_service_body(meta, with_filters=with_filters),
            footer="# Add custom service methods below.",
        ),
    )
    written.append(str(service_path.relative_to(ROOT)))

    router_path = module_dir / "router.py"
    existing_router = router_path.read_text(encoding="utf-8") if router_path.exists() else None
    write_file(
        router_path,
        merge_generated_content(
            existing_router,
            header=_router_header(
                meta, with_filters=with_filters, with_permissions=with_permissions
            ),
            body=_render_router_body(
                meta, with_filters=with_filters, with_permissions=with_permissions
            ),
            footer="# Add custom routes below.",
        ),
    )
    written.append(str(router_path.relative_to(ROOT)))

    if with_filters:
        filters_path = module_dir / "filters.py"
        write_file(filters_path, _render_filters(meta))
        written.append(str(filters_path.relative_to(ROOT)))

    if with_permissions:
        permissions_path = module_dir / "permissions.py"
        write_file(permissions_path, _render_permissions(meta))
        written.append(str(permissions_path.relative_to(ROOT)))
        written.extend(register_module_permissions(module_name))

    if with_tests:
        tests_path = ROOT / "tests" / f"test_{module_name}_crud.py"
        write_file(tests_path, _render_tests(meta, with_permissions=with_permissions))
        written.append(str(tests_path.relative_to(ROOT)))

    return written


def _uses_email(meta: ModelMeta) -> bool:
    return any(col.pydantic_type == "EmailStr" for col in meta.columns)


def _schema_imports(meta: ModelMeta) -> str:
    imports = ["from pydantic import BaseModel, ConfigDict, Field"]
    if _uses_email(meta):
        imports[0] = "from pydantic import BaseModel, ConfigDict, EmailStr, Field"
    dt_imports = []
    if any(col.pydantic_type == "datetime" for col in meta.columns):
        dt_imports.append("datetime")
    if any(col.pydantic_type == "date" for col in meta.columns):
        dt_imports.append("date")
    if dt_imports:
        imports.append(f"from datetime import {', '.join(dt_imports)}")
    return "\n".join(imports)


def _render_schemas(meta: ModelMeta) -> str:
    class_name = meta.class_name
    lines = [
        f'"""Pydantic schemas for the {meta.module_name} module (generated)."""',
        "",
        _schema_imports(meta),
        "",
        f"class {class_name}Create(BaseModel):",
    ]
    create_cols = create_fields(meta)
    if create_cols:
        lines.extend(render_field(col, required=not col.nullable) for col in create_cols)
    else:
        lines.append("    pass")
    lines.extend(["", f"class {class_name}Update(BaseModel):"])
    update_cols = update_fields(meta)
    if update_cols:
        lines.extend(render_field(col, required=False) for col in update_cols)
    else:
        lines.append("    pass")
    lines.extend(
        [
            "",
            f"class {class_name}Response(BaseModel):",
            "    model_config = ConfigDict(from_attributes=True)",
            "",
        ]
    )
    lines.extend(render_field(col, required=not col.nullable) for col in response_fields(meta))
    lines.append("")
    return "\n".join(lines)


def _repository_header(meta: ModelMeta, *, with_filters: bool) -> str:
    lines = [
        f'"""Data access for the {meta.module_name} module."""',
        "",
        "from sqlalchemy import Select, or_",
        "from sqlalchemy.ext.asyncio import AsyncSession",
        "",
        "from core.repository import BaseRepository",
        f"from {meta.model_import.rsplit('.', 1)[0]} import {meta.class_name}",
    ]
    if with_filters:
        lines.append(f"from modules.{meta.module_name}.filters import {meta.class_name}Filter")
    return "\n".join(lines)


def _render_repository_body(meta: ModelMeta, *, with_filters: bool) -> str:
    class_name = meta.class_name
    lines = [
        f"class {class_name}Repository(BaseRepository[{class_name}]):",
        f"    model = {class_name}",
        f"    soft_delete = {meta.soft_delete!r}",
        "",
        "    def __init__(self, db: AsyncSession):",
        "        super().__init__(db)",
    ]
    if with_filters:
        lines.extend(
            [
                "",
                f"    def apply_filters(self, stmt: Select, filters: {class_name}Filter) -> Select:",
                "        if filters.search:",
                "            clauses = []",
            ]
        )
        searchable = [col for col in meta.columns if col.searchable]
        for col in searchable:
            model_attr = f"{class_name}.{col.name}"
            lines.append(f'            clauses.append({model_attr}.ilike(f"%{{filters.search}}%"))')
        if searchable:
            lines.append("            stmt = stmt.where(or_(*clauses))")
        for col in filter_fields(meta):
            if col.pydantic_type == "bool":
                lines.append(f"        if filters.{col.name} is not None:")
                lines.append(
                    f"            stmt = stmt.where({class_name}.{col.name} == filters.{col.name})"
                )
            elif col.pydantic_type in {"datetime", "date"}:
                lines.append(f"        if filters.{col.name}_after is not None:")
                lines.append(
                    f"            stmt = stmt.where({class_name}.{col.name} >= filters.{col.name}_after)"
                )
                lines.append(f"        if filters.{col.name}_before is not None:")
                lines.append(
                    f"            stmt = stmt.where({class_name}.{col.name} <= filters.{col.name}_before)"
                )
            else:
                lines.append(f"        if filters.{col.name} is not None:")
                lines.append(
                    f"            stmt = stmt.where({class_name}.{col.name} == filters.{col.name})"
                )
        sort_default = default_sort_field(meta)
        lines.extend(
            [
                f'        sort_field = filters.sort or "{sort_default}"',
                "        sort_column = getattr(self.model, sort_field, None)",
                "        if sort_column is not None:",
                "            stmt = stmt.order_by(",
                '                sort_column.asc() if filters.order == "asc" else sort_column.desc()',
                "            )",
                "        return stmt",
                "",
                "    async def list_filtered(",
                "        self,",
                "        *,",
                "        skip: int,",
                "        limit: int,",
                f"        filters: {class_name}Filter,",
                f"    ) -> tuple[list[{class_name}], int]:",
                "        stmt = self.apply_filters(self._base_query(), filters)",
                "        return await self.list(skip=skip, limit=limit, stmt=stmt)",
            ]
        )
    return "\n".join(lines)


def _service_header(meta: ModelMeta, *, with_filters: bool) -> str:
    class_name = meta.class_name
    lines = [
        f'"""Business logic for the {meta.module_name} module."""',
        "",
        "from fastapi import HTTPException, status",
        "from sqlalchemy.ext.asyncio import AsyncSession",
        "",
        "from core.pagination import Page, PageParams, build_page",
        f"from modules.{meta.module_name}.repository import {class_name}Repository",
        f"from modules.{meta.module_name}.schemas import {class_name}Create, {class_name}Response, {class_name}Update",
    ]
    if with_filters:
        lines.append(f"from modules.{meta.module_name}.filters import {class_name}Filter")
    return "\n".join(lines)


def _render_service_body(meta: ModelMeta, *, with_filters: bool) -> str:
    class_name = meta.class_name
    create_data = ", ".join(f"{col.name}=data.{col.name}" for col in create_fields(meta))
    update_data = ", ".join(f"{col.name}=data.{col.name}" for col in update_fields(meta))
    lines = [
        f"class {class_name}Service:",
        "    def __init__(self, db: AsyncSession):",
        "        self.db = db",
        f"        self.repo = {class_name}Repository(db)",
        "",
        f"    async def create(self, data: {class_name}Create) -> {class_name}Response:",
        f"        item = await self.repo.create({create_data})",
        "        await self.db.commit()",
        f"        return {class_name}Response.model_validate(item)",
        "",
        f"    async def get(self, item_id: int) -> {class_name}Response:",
        "        item = await self.repo.get_by_id(item_id)",
        "        if item is None:",
        '            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Not found")',
        f"        return {class_name}Response.model_validate(item)",
        "",
        "    async def list(self, params: PageParams",
    ]
    if with_filters:
        lines[-1] += f", filters: {class_name}Filter"
    lines[-1] += f") -> Page[{class_name}Response]:"
    if with_filters:
        lines.extend(
            [
                "        items, total = await self.repo.list_filtered(",
                "            skip=params.offset,",
                "            limit=params.page_size,",
                "            filters=filters,",
                "        )",
            ]
        )
    else:
        sort_default = default_sort_field(meta)
        lines.extend(
            [
                f"        stmt = self.repo._base_query().order_by(self.repo.model.{sort_default}.desc())",
                "        items, total = await self.repo.list(",
                "            skip=params.offset,",
                "            limit=params.page_size,",
                "            stmt=stmt,",
                "        )",
            ]
        )
    lines.extend(
        [
            f"        return build_page([{class_name}Response.model_validate(i) for i in items], total, params)",
            "",
            f"    async def update(self, item_id: int, data: {class_name}Update) -> {class_name}Response:",
            "        item = await self.repo.get_by_id(item_id)",
            "        if item is None:",
            '            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Not found")',
            f"        item = await self.repo.update(item, {update_data})",
            "        await self.db.commit()",
            f"        return {class_name}Response.model_validate(item)",
            "",
            "    async def delete(self, item_id: int) -> None:",
            "        item = await self.repo.get_by_id(item_id)",
            "        if item is None:",
            '            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Not found")',
            "        await self.repo.delete(item)",
            "        await self.db.commit()",
        ]
    )
    return "\n".join(lines)


def _router_header(meta: ModelMeta, *, with_filters: bool, with_permissions: bool) -> str:
    class_name = meta.class_name
    lines = [
        f'"""Routes for the {meta.module_name} module."""',
        "",
        "from fastapi import APIRouter, Depends, status",
        "from sqlalchemy.ext.asyncio import AsyncSession",
        "",
        "from core.dependencies import get_db",
        "from core.pagination import Page, PageParams",
    ]
    if with_permissions:
        lines.append("from core.permissions import PermissionCodename, require_permission")
    else:
        lines.append("from core.dependencies import get_current_user")
    if with_filters:
        lines.append(f"from modules.{meta.module_name}.filters import {class_name}Filter")
    lines.extend(
        [
            f"from modules.{meta.module_name}.schemas import {class_name}Create, {class_name}Response, {class_name}Update",
            f"from modules.{meta.module_name}.service import {class_name}Service",
            "from database.models.user import User",
            "",
            f'router = APIRouter(prefix="{meta.route_prefix}", tags=["{meta.module_name}"])',
        ]
    )
    return "\n".join(lines)


def _auth_dep(permission: str, with_permissions: bool) -> str:
    if with_permissions:
        return f"Depends(require_permission({permission}))"
    return "Depends(get_current_user)"


def _render_router_body(meta: ModelMeta, *, with_filters: bool, with_permissions: bool) -> str:
    class_name = meta.class_name
    read_dep = _auth_dep(
        f"PermissionCodename.{enum_member(meta.module_name, 'READ')}.value", with_permissions
    )
    create_dep = _auth_dep(
        f"PermissionCodename.{enum_member(meta.module_name, 'CREATE')}.value", with_permissions
    )
    update_dep = _auth_dep(
        f"PermissionCodename.{enum_member(meta.module_name, 'UPDATE')}.value", with_permissions
    )
    delete_dep = _auth_dep(
        f"PermissionCodename.{enum_member(meta.module_name, 'DELETE')}.value", with_permissions
    )

    list_sig = [
        '@router.get("", response_model=Page[' + f"{class_name}Response])",
        "async def list_items(",
        "    params: PageParams = Depends(),",
    ]
    if with_filters:
        list_sig.append(f"    filters: {class_name}Filter = Depends(),")
    list_sig.extend(
        [
            "    db: AsyncSession = Depends(get_db),",
            f"    _user: User = {read_dep},",
            "):",
            f"    service = {class_name}Service(db)",
        ]
    )
    if with_filters:
        list_sig.append("    return await service.list(params, filters)")
    else:
        list_sig.append("    return await service.list(params)")

    return "\n".join(
        [
            *list_sig,
            "",
            f'@router.post("", response_model={class_name}Response, status_code=status.HTTP_201_CREATED)',
            "async def create_item(",
            f"    data: {class_name}Create,",
            "    db: AsyncSession = Depends(get_db),",
            f"    _user: User = {create_dep},",
            "):",
            f"    service = {class_name}Service(db)",
            "    return await service.create(data)",
            "",
            f'@router.get("/{{item_id}}", response_model={class_name}Response)',
            "async def get_item(",
            "    item_id: int,",
            "    db: AsyncSession = Depends(get_db),",
            f"    _user: User = {read_dep},",
            "):",
            f"    service = {class_name}Service(db)",
            "    return await service.get(item_id)",
            "",
            f'@router.patch("/{{item_id}}", response_model={class_name}Response)',
            "async def update_item(",
            "    item_id: int,",
            f"    data: {class_name}Update,",
            "    db: AsyncSession = Depends(get_db),",
            f"    _user: User = {update_dep},",
            "):",
            f"    service = {class_name}Service(db)",
            "    return await service.update(item_id, data)",
            "",
            '@router.delete("/{item_id}", status_code=status.HTTP_204_NO_CONTENT)',
            "async def delete_item(",
            "    item_id: int,",
            "    db: AsyncSession = Depends(get_db),",
            f"    _user: User = {delete_dep},",
            "):",
            f"    service = {class_name}Service(db)",
            "    await service.delete(item_id)",
        ]
    )


def _render_filters(meta: ModelMeta) -> str:
    class_name = meta.class_name
    uses_date = any(col.pydantic_type == "date" for col in filter_fields(meta))
    uses_datetime = any(col.pydantic_type == "datetime" for col in filter_fields(meta))
    date_imports = []
    if uses_date:
        date_imports.append("date")
    if uses_datetime:
        date_imports.append("datetime")

    lines = [
        f'"""List filters for the {meta.module_name} module (generated)."""',
        "",
    ]
    if date_imports:
        lines.append(f"from datetime import {', '.join(date_imports)}")
        lines.append("")
    lines.extend(
        [
            "from pydantic import Field",
            "",
            "from core.filters import BaseFilter",
            "",
            f"class {class_name}Filter(BaseFilter):",
            f'    sort: str | None = Field(default=None, description="Sort field (default: {default_sort_field(meta)})")',
        ]
    )
    for col in filter_fields(meta):
        if col.pydantic_type in {"datetime", "date"}:
            type_name = "datetime" if col.pydantic_type == "datetime" else "date"
            lines.append(f"    {col.name}_after: {type_name} | None = None")
            lines.append(f"    {col.name}_before: {type_name} | None = None")
        else:
            lines.append(f"    {col.name}: {col.pydantic_type} | None = None")
    lines.append("")
    return "\n".join(lines)


def _render_permissions(meta: ModelMeta) -> str:
    prefix = enum_prefix(meta.module_name)
    return (
        f'"""Permission codenames for the {meta.module_name} module (generated)."""\n\n'
        f"from core.permissions import PermissionCodename\n\n"
        f"CREATE = PermissionCodename.{prefix}_CREATE\n"
        f"READ = PermissionCodename.{prefix}_READ\n"
        f"UPDATE = PermissionCodename.{prefix}_UPDATE\n"
        f"DELETE = PermissionCodename.{prefix}_DELETE\n"
    )


def _render_tests(meta: ModelMeta, *, with_permissions: bool) -> str:
    route = meta.route_prefix
    api_prefix = "/api/v1"
    create_cols = create_fields(meta)
    sample_payload_lines = []
    for col in create_cols:
        if col.pydantic_type == "bool":
            sample_payload_lines.append(f'        "{col.name}": True,')
        elif col.pydantic_type == "int":
            sample_payload_lines.append(f'        "{col.name}": 1,')
        elif col.pydantic_type == "float":
            sample_payload_lines.append(f'        "{col.name}": 9.99,')
        elif col.pydantic_type == "EmailStr":
            sample_payload_lines.append(
                f'        "{col.name}": f"{col.name}-{{uuid.uuid4().hex[:6]}}@example.com",'
            )
        else:
            sample_payload_lines.append(f'        "{col.name}": "Sample {col.name}",')
    payload_block = "\n".join(sample_payload_lines) if sample_payload_lines else "        pass"

    update_col = next((col for col in update_fields(meta) if col.pydantic_type == "str"), None)
    update_payload = (
        f'{{"{update_col.name}": "Updated value"}}' if update_col else '{"title": "Updated value"}'
    )

    perm_note = ""
    if with_permissions:
        perm_note = "\n# NOTE: Run `python manage.py seed-data` before these tests.\n"

    return (
        f'"""CRUD tests for {meta.module_name} (generated)."""\n'
        f"{perm_note}\n"
        f"import uuid\n\n"
        f"import pytest\n\n\n"
        f"def _email(prefix: str) -> str:\n"
        f'    return f"{{prefix}}-{{uuid.uuid4().hex[:8]}}@example.com"\n\n\n'
        f"async def _auth_headers(client):\n"
        f'    email = _email("{meta.module_name}")\n'
        f'    password = "testpass123"\n'
        f"    await client.post(\n"
        f'        "{api_prefix}/auth/register",\n'
        f'        json={{"email": email, "password": password}},\n'
        f"    )\n"
        f"    login = await client.post(\n"
        f'        "{api_prefix}/auth/login",\n'
        f'        json={{"email": email, "password": password}},\n'
        f"    )\n"
        f'    token = login.json()["access_token"]\n'
        f'    return {{"Authorization": f"Bearer {{token}}", "Content-Type": "application/json"}}\n\n\n'
        f"@pytest.mark.asyncio\n"
        f"async def test_{meta.module_name}_crud(client):\n"
        f"    headers = await _auth_headers(client)\n\n"
        f"    create = await client.post(\n"
        f'        "{api_prefix}{route}",\n'
        f"        headers=headers,\n"
        f"        json={{\n"
        f"{payload_block}\n"
        f"        }},\n"
        f"    )\n"
        f"    assert create.status_code == 201\n"
        f"    item = create.json()\n"
        f'    assert "id" in item\n\n'
        f"    get_one = await client.get(\n"
        f"        f\"{api_prefix}{route}/{{item['id']}}\",\n"
        f"        headers=headers,\n"
        f"    )\n"
        f"    assert get_one.status_code == 200\n\n"
        f"    listed = await client.get(\n"
        f'        "{api_prefix}{route}",\n'
        f"        headers=headers,\n"
        f"    )\n"
        f"    assert listed.status_code == 200\n"
        f'    assert listed.json()["total"] >= 1\n\n'
        f"    updated = await client.patch(\n"
        f"        f\"{api_prefix}{route}/{{item['id']}}\",\n"
        f"        headers=headers,\n"
        f"        json={update_payload},\n"
        f"    )\n"
        f"    assert updated.status_code == 200\n\n"
        f"    deleted = await client.delete(\n"
        f"        f\"{api_prefix}{route}/{{item['id']}}\",\n"
        f"        headers=headers,\n"
        f"    )\n"
        f"    assert deleted.status_code == 204\n"
    )


def _ensure_model_registered(meta: ModelMeta) -> None:
    """Ensure model is imported in database/models/__init__.py and alembic/env.py."""
    init_path = ROOT / "database" / "models" / "__init__.py"
    init_text = init_path.read_text(encoding="utf-8")
    import_line = f"from database.models.{meta.module_name} import {meta.class_name}"
    if import_line not in init_text:
        lines = init_text.splitlines()
        insert_at = len(lines)
        for idx, line in enumerate(lines):
            if line.startswith("__all__"):
                insert_at = idx
                break
        lines.insert(insert_at, import_line)
        lines.insert(insert_at, "")
        for idx, line in enumerate(lines):
            if line.startswith("__all__"):
                if meta.class_name not in line:
                    line = line.rstrip("]")
                    if line.endswith("["):
                        lines[idx] = f'{line}"{meta.class_name}"]'
                    else:
                        lines[idx] = f'{line}, "{meta.class_name}"]'
                break
        init_path.write_text("\n".join(lines) + "\n", encoding="utf-8")

    env_path = ROOT / "alembic" / "env.py"
    env_text = env_path.read_text(encoding="utf-8")
    env_import = f"    {meta.module_name},"
    if env_import not in env_text:
        marker = (
            "from database.models import (  # noqa: F401 — register all models for autogenerate"
        )
        if marker in env_text:
            env_text = env_text.replace(
                marker,
                f"{marker}\n{env_import}",
            )
            env_path.write_text(env_text, encoding="utf-8")


def _registration_notes(meta: ModelMeta) -> list[str]:
    return [
        str((ROOT / "database" / "models" / "__init__.py").relative_to(ROOT)),
        str((ROOT / "alembic" / "env.py").relative_to(ROOT)),
    ]
