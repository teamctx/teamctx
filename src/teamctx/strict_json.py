"""Strict JSON parsing shared by team config and declared records."""

from __future__ import annotations

import json
from typing import Any


class StrictJsonError(ValueError):
    """Raised when JSON is syntactically valid enough to parse but violates teamctx caps."""


def loads_strict_json(
    raw: str | bytes,
    *,
    source: str,
    max_bytes: int | None = None,
    max_depth: int | None = None,
) -> Any:
    """Parse JSON while rejecting duplicate object keys and enforcing optional caps."""

    if isinstance(raw, bytes):
        if max_bytes is not None and len(raw) > max_bytes:
            raise StrictJsonError(f"{source} is too large; maximum is {max_bytes} bytes")
        try:
            text = raw.decode("utf-8")
        except UnicodeDecodeError as exc:
            raise StrictJsonError(f"{source} is not valid UTF-8") from exc
    else:
        text = raw
        if max_bytes is not None and len(text.encode("utf-8")) > max_bytes:
            raise StrictJsonError(f"{source} is too large; maximum is {max_bytes} bytes")

    def object_pairs(pairs: list[tuple[str, Any]]) -> dict[str, Any]:
        result: dict[str, Any] = {}
        for key, value in pairs:
            if key in result:
                raise StrictJsonError(f"{source} has duplicate object key {key!r}")
            result[key] = value
        return result

    try:
        data = json.loads(text, object_pairs_hook=object_pairs)
    except StrictJsonError:
        raise
    except json.JSONDecodeError as exc:
        raise StrictJsonError(f"{source} is not valid JSON") from exc

    if max_depth is not None:
        depth = _json_depth(data)
        if depth > max_depth:
            raise StrictJsonError(
                f"{source} is too deeply nested; maximum depth is {max_depth}"
            )
    return data


def _json_depth(value: Any) -> int:
    if isinstance(value, dict):
        if not value:
            return 1
        return 1 + max(_json_depth(child) for child in value.values())
    if isinstance(value, list):
        if not value:
            return 1
        return 1 + max(_json_depth(child) for child in value)
    return 1
