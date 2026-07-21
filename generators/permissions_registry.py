"""Register generated module permissions in core platform files."""

from __future__ import annotations

import re
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent

PERM_BEGIN = "# --- BEGIN GENERATED PERMISSIONS ---"
PERM_END = "# --- END GENERATED PERMISSIONS ---"
SEED_BEGIN = "# --- BEGIN GENERATED USER PERMISSIONS ---"
SEED_END = "# --- END GENERATED USER PERMISSIONS ---"

PERM_ACTIONS = ("CREATE", "READ", "UPDATE", "DELETE")
USER_ROLE_ACTIONS = PERM_ACTIONS


def enum_prefix(module_name: str) -> str:
    return module_name.upper()


def enum_member(module_name: str, action: str) -> str:
    return f"{enum_prefix(module_name)}_{action}"


def codename(module_name: str, action: str) -> str:
    return f"{module_name}.{action.lower()}"


def register_module_permissions(module_name: str) -> list[str]:
    """Add or refresh a module's permissions in core files. Returns updated paths."""
    updated: list[str] = []

    perm_path = ROOT / "core" / "permissions.py"
    perm_text = perm_path.read_text(encoding="utf-8")
    perm_text = _ensure_enum_markers(perm_text)
    modules = _parse_enum_permissions(perm_text)
    modules[module_name] = {action: codename(module_name, action) for action in PERM_ACTIONS}
    perm_path.write_text(_render_enum_permissions(perm_text, modules), encoding="utf-8")
    updated.append(str(perm_path.relative_to(ROOT)))

    seed_path = ROOT / "database" / "seed.py"
    seed_text = seed_path.read_text(encoding="utf-8")
    seed_text = _ensure_seed_markers(seed_text)
    seed_modules = _parse_seed_user_permissions(seed_text)
    seed_modules[module_name] = list(USER_ROLE_ACTIONS)
    seed_path.write_text(_render_seed_user_permissions(seed_text, seed_modules), encoding="utf-8")
    updated.append(str(seed_path.relative_to(ROOT)))

    return updated


def _ensure_enum_markers(content: str) -> str:
    if PERM_BEGIN in content:
        return content
    anchor = '    ADMIN_ACCESS = "admin.access"\n'
    if anchor not in content:
        raise ValueError("Could not locate PermissionCodename anchor in core/permissions.py")
    return content.replace(
        anchor,
        f"{anchor}\n    {PERM_BEGIN}\n    {PERM_END}\n",
    )


def _ensure_seed_markers(content: str) -> str:
    if SEED_BEGIN in content:
        return content
    anchor = "                PermissionCodename.PAYMENTS_CREATE.value,\n"
    if anchor not in content:
        raise ValueError("Could not locate user role permissions anchor in database/seed.py")
    return content.replace(
        anchor,
        f"{anchor}                {SEED_BEGIN}\n                {SEED_END}\n",
    )


def _line_indent(line: str) -> str:
    stripped = line.lstrip()
    if not stripped:
        return ""
    return line[: line.index(stripped[0])]


def _parse_enum_permissions(content: str) -> dict[str, dict[str, str]]:
    block = _extract_block(content, PERM_BEGIN, PERM_END)
    modules: dict[str, dict[str, str]] = {}
    for line in block.splitlines():
        match = re.match(r'\s+([A-Z0-9_]+)\s*=\s*"([^"]+)"', line)
        if not match:
            continue
        member, value = match.groups()
        if "." not in value:
            continue
        module_name, action = value.rsplit(".", 1)
        modules.setdefault(module_name, {})[action.upper()] = value
    return modules


def _parse_seed_user_permissions(content: str) -> dict[str, list[str]]:
    block = _extract_block(content, SEED_BEGIN, SEED_END)
    modules: dict[str, list[str]] = {}
    for line in block.splitlines():
        match = re.search(r"PermissionCodename\.([A-Z0-9_]+)\.value", line)
        if not match:
            continue
        member = match.group(1)
        for action in PERM_ACTIONS:
            suffix = f"_{action}"
            if member.endswith(suffix):
                module_name = member[: -len(suffix)].lower()
                modules.setdefault(module_name, [])
                if action not in modules[module_name]:
                    modules[module_name].append(action)
                break
    return modules


def _extract_block(content: str, begin: str, end: str) -> str:
    if begin not in content or end not in content:
        return ""
    return content.split(begin, 1)[1].split(end, 1)[0]


def _replace_block(content: str, begin: str, end: str, body: str) -> str:
    if begin not in content or end not in content:
        raise ValueError(f"Missing markers {begin} / {end}")

    lines = content.splitlines(keepends=True)
    begin_idx = next(i for i, line in enumerate(lines) if begin in line)
    end_idx = next(i for i, line in enumerate(lines) if end in line)
    indent = _line_indent(lines[begin_idx])

    new_lines = lines[: begin_idx + 1]
    if body.strip():
        if not body.endswith("\n"):
            body += "\n"
        new_lines.append(body)
    new_lines.append(f"{indent}{end}\n")
    new_lines.extend(lines[end_idx + 1 :])
    return "".join(new_lines)


def _render_enum_permissions(content: str, modules: dict[str, dict[str, str]]) -> str:
    lines: list[str] = []
    for module_name in sorted(modules):
        perms = modules[module_name]
        for action in PERM_ACTIONS:
            if action in perms:
                member = enum_member(module_name, action)
                lines.append(f'    {member} = "{perms[action]}"')
    body = "\n".join(lines)
    return _replace_block(content, PERM_BEGIN, PERM_END, body)


def _render_seed_user_permissions(content: str, modules: dict[str, list[str]]) -> str:
    lines: list[str] = []
    for module_name in sorted(modules):
        for action in USER_ROLE_ACTIONS:
            member = enum_member(module_name, action)
            lines.append(f"                PermissionCodename.{member}.value,")
    body = "\n".join(lines)
    return _replace_block(content, SEED_BEGIN, SEED_END, body)