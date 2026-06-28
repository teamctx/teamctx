from __future__ import annotations

from datetime import datetime

from teamctx.clock import utc_now_iso


def test_ends_with_z() -> None:
    assert utc_now_iso().endswith("Z")


def test_no_plus_zero_offset() -> None:
    assert "+00:00" not in utc_now_iso()


def test_no_microseconds() -> None:
    value = utc_now_iso()
    # The time part follows the 'T'; a dot would indicate sub-second precision.
    time_part = value.split("T", 1)[1]
    assert "." not in time_part


def test_parses_back_to_datetime() -> None:
    value = utc_now_iso()
    parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    assert parsed.microsecond == 0
    assert parsed.tzinfo is not None
