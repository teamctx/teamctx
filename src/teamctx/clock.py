"""UTC timestamp helper, shared so the format is identical across every transport. Stdlib only,
so the hot hook path can import it without pulling the broker."""

from __future__ import annotations

from datetime import UTC, datetime


def utc_now_iso() -> str:
    """Current UTC time as an ISO 8601 string with a trailing ``Z``, seconds precision."""

    return datetime.now(UTC).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def parse_since(text: str) -> datetime:
    """Parse a work-start ``since`` timestamp, normalizing naive/date-only values to UTC."""

    try:
        parsed = datetime.fromisoformat(text)
    except ValueError as exc:
        raise ValueError(
            f"--since {text!r} is not an ISO-8601 timestamp "
            "(e.g. 2026-07-01 or 2026-07-01T12:00:00Z)."
        ) from exc
    parsed = parsed.replace(tzinfo=UTC) if parsed.tzinfo is None else parsed.astimezone(UTC)
    return parsed
