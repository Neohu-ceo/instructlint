from __future__ import annotations

import re
from typing import Any


def _scalar(value: str) -> Any:
    value = value.strip()
    if not value:
        return ""
    if value.lower() in {"true", "false"}:
        return value.lower() == "true"
    if value.startswith("[") and value.endswith("]"):
        inner = value[1:-1].strip()
        if not inner:
            return []
        return [item.strip().strip("'\"") for item in inner.split(",")]
    return value.strip("'\"")


def parse_frontmatter(text: str) -> tuple[dict[str, Any], str, int, str | None]:
    """Parse the small YAML subset used by common agent rule formats.

    Returns metadata, body, body line offset, and an optional error. Avoiding a
    YAML dependency keeps the CLI install-free while covering scalar and list
    fields such as globs, paths, and applyTo.
    """

    lines = text.splitlines()
    if not lines or lines[0].strip() != "---":
        return {}, text, 0, None

    closing_index = next(
        (
            index
            for index, line in enumerate(lines[1:], start=1)
            if line.strip() == "---"
        ),
        None,
    )
    if closing_index is None:
        return {}, text, 0, "frontmatter starts with --- but has no closing ---"

    metadata: dict[str, Any] = {}
    active_list: str | None = None
    for raw_line in lines[1:closing_index]:
        line = raw_line.rstrip()
        if not line.strip() or line.lstrip().startswith("#"):
            continue
        list_match = re.match(r"^\s*-\s+(.+?)\s*$", line)
        if list_match and active_list:
            value = list_match.group(1).strip("'\"")
            existing = metadata.setdefault(active_list, [])
            if isinstance(existing, list):
                existing.append(value)
            continue
        key_match = re.match(r"^([A-Za-z][\w-]*):\s*(.*?)\s*$", line)
        if not key_match:
            # Valid YAML can contain folded continuations and nested structures.
            # They are irrelevant to scope detection, so keep parsing permissive
            # instead of mislabelling a format we intentionally do not implement.
            if line[:1].isspace():
                continue
            return {}, text, 0, f"invalid frontmatter line: {line.strip()}"
        key, raw_value = key_match.groups()
        if raw_value:
            metadata[key] = _scalar(raw_value)
            active_list = None
        else:
            metadata[key] = []
            active_list = key

    body = "\n".join(lines[closing_index + 1 :])
    if text.endswith("\n"):
        body += "\n"
    return metadata, body, closing_index + 1, None
