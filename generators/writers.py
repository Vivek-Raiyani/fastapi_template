"""File writers with generated-code markers for safe regeneration."""

BEGIN_GENERATED = "# --- BEGIN GENERATED ---"
END_GENERATED = "# --- END GENERATED ---"


def extract_custom_suffix(existing: str | None) -> str:
    """Return content after the generated block (custom routes, methods, etc.)."""
    if not existing or END_GENERATED not in existing:
        return ""
    return existing[existing.index(END_GENERATED) + len(END_GENERATED) :]


def merge_generated_content(
    existing: str | None,
    *,
    header: str,
    body: str,
    footer: str = "",
) -> str:
    """Replace header and generated body; preserve custom content after markers."""
    generated_block = f"{BEGIN_GENERATED}\n{body}\n{END_GENERATED}"
    custom_suffix = extract_custom_suffix(existing).rstrip()
    if not custom_suffix and footer:
        custom_suffix = footer.rstrip()

    parts = [header.rstrip(), "", generated_block]
    if custom_suffix:
        parts.extend(["", custom_suffix])
    return "\n".join(parts) + "\n"


def write_file(path, content: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content, encoding="utf-8")
