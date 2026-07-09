from __future__ import annotations

from datetime import UTC, datetime

import pytest

from teamctx.clock import parse_since, utc_now_iso


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


def test_parse_since_accepts_z_offset_naive_and_date_only() -> None:
    assert parse_since("2026-07-01T12:00:00Z") == datetime(2026, 7, 1, 12, tzinfo=UTC)
    assert parse_since("2026-07-01T14:00:00+02:00") == datetime(2026, 7, 1, 12, tzinfo=UTC)
    assert parse_since("2026-07-01T12:00:00") == datetime(2026, 7, 1, 12, tzinfo=UTC)
    assert parse_since("2026-07-01") == datetime(2026, 7, 1, tzinfo=UTC)


def test_parse_since_invalid_value_raises_pinned_message() -> None:
    with pytest.raises(ValueError) as exc:
        parse_since("July 1")

    assert str(exc.value) == (
        "--since 'July 1' is not an ISO-8601 timestamp "
        "(e.g. 2026-07-01 or 2026-07-01T12:00:00Z)."
    )
