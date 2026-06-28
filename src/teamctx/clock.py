"""UTC timestamp helper, shared so the format is identical across every transport. Stdlib only,
so the hot hook path can import it without pulling the broker."""

from __future__ import annotations

from datetime import UTC, datetime


def utc_now_iso() -> str:
    """Current UTC time as an ISO 8601 string with a trailing ``Z``, seconds precision."""

    return datetime.now(UTC).replace(microsecond=0).isoformat().replace("+00:00", "Z")
