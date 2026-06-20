"""Narrow docs-supersession probe: read declared supersession from markdown frontmatter."""

from __future__ import annotations


def parse_frontmatter(text: str) -> dict[str, str]:
    """Parse a leading ``---`` fenced ``key: value`` block. No YAML dependency: only
    top-level string scalars are read, the block ends at the first closing ``---``, and a
    file without a leading ``---`` has no frontmatter."""

    lines = text.splitlines()
    if not lines or lines[0].strip() != "---":
        return {}
    fields: dict[str, str] = {}
    for line in lines[1:]:
        if line.strip() == "---":
            break
        if ":" not in line:
            continue
        key, _, value = line.partition(":")
        fields[key.strip()] = value.strip()
    return fields
