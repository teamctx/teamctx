import json

from teamctx.connectors.github_issues import (
    _build_detail,
    _parse_issue_number,
    fetch_issue_changes,
    run_github_issues_probe,
)
from teamctx.core.contracts import RequestContext

OBSERVED = "2026-06-25T12:00:00Z"
SINCE = "2026-06-24T00:00:00Z"


def _request(linked: list[str] | None = None) -> RequestContext:
    return RequestContext(
        schema_version="teamctx.request_context.v0",
        request_id="test",
        repo="teamctx/teamctx",
        task="test",
        paths=["src/teamctx/cli.py"],
        linked_issues=linked or ["#42"],
        requested_at=OBSERVED,
        requesting_principal=None,
    )


def _fake_opener(responses: dict[str, object]):
    """Return an opener that maps URL substrings to JSON responses."""

    class FakeResponse:
        def __init__(self, data: object) -> None:
            self._data = data

        def read(self) -> bytes:
            return json.dumps(self._data).encode()

        def __enter__(self):
            return self

        def __exit__(self, *a):
            pass

    def opener(request):
        url = request.full_url
        best_pattern = ""
        best_data: object = {}
        for pattern, data in responses.items():
            if pattern in url and len(pattern) > len(best_pattern):
                best_pattern = pattern
                best_data = data
        return FakeResponse(best_data)

    return opener


def _issue_payload(
    number: int = 42,
    updated_at: str = "2026-06-25T10:00:00Z",
    state: str = "open",
    title: str = "Add widget support",
    labels: list[dict] | None = None,
) -> dict:
    return {
        "number": number,
        "updated_at": updated_at,
        "state": state,
        "title": title,
        "html_url": f"https://github.com/teamctx/teamctx/issues/{number}",
        "labels": labels or [],
    }


def _events_payload(events: list[dict] | None = None) -> list[dict]:
    return events or []


def test_fetch_detects_body_edit() -> None:
    opener = _fake_opener({
        "/issues/42": _issue_payload(updated_at="2026-06-25T10:00:00Z"),
        "/issues/42/events": _events_payload(),
    })
    changes = fetch_issue_changes(
        repo="teamctx/teamctx", issues=["#42"], since=SINCE,
        token="t", opener=opener,
    )
    assert len(changes) == 1
    assert changes[0].change_kinds == ("body_edited",)
    assert "description or comments" in changes[0].detail


def test_fetch_detects_state_change() -> None:
    opener = _fake_opener({
        "/issues/42": _issue_payload(state="closed"),
        "/issues/42/events": _events_payload([
            {"event": "closed", "created_at": "2026-06-25T09:00:00Z"},
        ]),
    })
    changes = fetch_issue_changes(
        repo="teamctx/teamctx", issues=["#42"], since=SINCE,
        token="t", opener=opener,
    )
    assert len(changes) == 1
    assert "state_changed" in changes[0].change_kinds
    assert "state is now closed" in changes[0].detail


def test_fetch_detects_label_change() -> None:
    opener = _fake_opener({
        "/issues/42": _issue_payload(labels=[{"name": "critical"}]),
        "/issues/42/events": _events_payload([
            {"event": "labeled", "created_at": "2026-06-25T09:00:00Z"},
        ]),
    })
    changes = fetch_issue_changes(
        repo="teamctx/teamctx", issues=["#42"], since=SINCE,
        token="t", opener=opener,
    )
    assert len(changes) == 1
    assert "labels_changed" in changes[0].change_kinds
    assert "critical" in changes[0].detail


def test_fetch_skips_unchanged_issue() -> None:
    opener = _fake_opener({
        "/issues/42": _issue_payload(updated_at="2026-06-23T10:00:00Z"),
    })
    changes = fetch_issue_changes(
        repo="teamctx/teamctx", issues=["#42"], since=SINCE,
        token="t", opener=opener,
    )
    assert len(changes) == 0


def test_fetch_skips_invalid_issue_ref() -> None:
    opener = _fake_opener({})
    changes = fetch_issue_changes(
        repo="teamctx/teamctx", issues=["not-a-number"], since=SINCE,
        token="t", opener=opener,
    )
    assert len(changes) == 0


def test_fetch_multiple_issues() -> None:
    opener = _fake_opener({
        "/issues/42": _issue_payload(number=42, updated_at="2026-06-25T10:00:00Z"),
        "/issues/42/events": _events_payload(),
        "/issues/99": _issue_payload(number=99, updated_at="2026-06-25T11:00:00Z", title="Fix bug"),
        "/issues/99/events": _events_payload([
            {"event": "closed", "created_at": "2026-06-25T09:00:00Z"},
        ]),
    })
    changes = fetch_issue_changes(
        repo="teamctx/teamctx", issues=["#42", "#99"], since=SINCE,
        token="t", opener=opener,
    )
    assert len(changes) == 2


def test_events_before_since_are_ignored() -> None:
    opener = _fake_opener({
        "/issues/42": _issue_payload(updated_at="2026-06-25T10:00:00Z"),
        "/issues/42/events": _events_payload([
            {"event": "closed", "created_at": "2026-06-23T09:00:00Z"},
        ]),
    })
    changes = fetch_issue_changes(
        repo="teamctx/teamctx", issues=["#42"], since=SINCE,
        token="t", opener=opener,
    )
    assert len(changes) == 1
    assert changes[0].change_kinds == ("body_edited",)


def test_issue_updated_at_comparison_is_chronological_not_lexical() -> None:
    opener = _fake_opener({
        "/issues/42": _issue_payload(updated_at="2026-07-01T10:30:00Z"),
        "/issues/42/events": _events_payload(),
    })

    changes = fetch_issue_changes(
        repo="teamctx/teamctx",
        issues=["#42"],
        since="2026-07-01T12:00:00+02:00",
        token="t",
        opener=opener,
    )

    assert len(changes) == 1


def test_event_created_at_comparison_is_chronological_not_lexical() -> None:
    opener = _fake_opener({
        "/issues/42": _issue_payload(updated_at="2026-07-01T10:45:00Z"),
        "/issues/42/events": _events_payload([
            {"event": "closed", "created_at": "2026-07-01T10:30:00Z"},
        ]),
    })

    changes = fetch_issue_changes(
        repo="teamctx/teamctx",
        issues=["#42"],
        since="2026-07-01T12:00:00+02:00",
        token="t",
        opener=opener,
    )

    assert len(changes) == 1
    assert changes[0].change_kinds == ("state_changed",)


def test_unparseable_github_issue_timestamp_surfaces_the_change() -> None:
    opener = _fake_opener({
        "/issues/42": _issue_payload(updated_at="not-a-timestamp"),
        "/issues/42/events": _events_payload(),
    })

    changes = fetch_issue_changes(
        repo="teamctx/teamctx", issues=["#42"], since=SINCE, token="t", opener=opener,
    )

    assert len(changes) == 1
    assert changes[0].change_kinds == ("body_edited",)


def test_unparseable_github_event_timestamp_surfaces_the_change_kind() -> None:
    opener = _fake_opener({
        "/issues/42": _issue_payload(updated_at="2026-06-25T10:00:00Z"),
        "/issues/42/events": _events_payload([
            {"event": "closed", "created_at": "not-a-timestamp"},
        ]),
    })

    changes = fetch_issue_changes(
        repo="teamctx/teamctx", issues=["#42"], since=SINCE, token="t", opener=opener,
    )

    assert len(changes) == 1
    assert changes[0].change_kinds == ("state_changed",)


def test_probe_without_token_returns_unavailable() -> None:
    doc = run_github_issues_probe(
        repo="teamctx/teamctx", issues=["#42"], since=SINCE,
        token=None, request_context=_request(), observed_at=OBSERVED,
    )
    assert doc.source_statuses[0].status == "unavailable"
    assert len(doc.source_signals) == 0


def test_probe_with_no_issues_returns_fresh_empty() -> None:
    doc = run_github_issues_probe(
        repo="teamctx/teamctx", issues=[], since=SINCE,
        token="t", request_context=_request(), observed_at=OBSERVED,
    )
    assert doc.source_statuses[0].status == "fresh"
    assert len(doc.source_signals) == 0


def test_probe_surfaces_criteria_changed_signal() -> None:
    opener = _fake_opener({
        "/issues/42": _issue_payload(updated_at="2026-06-25T10:00:00Z"),
        "/issues/42/events": _events_payload(),
    })
    doc = run_github_issues_probe(
        repo="teamctx/teamctx", issues=["#42"], since=SINCE,
        token="t", request_context=_request(), observed_at=OBSERVED,
        opener=opener,
    )
    assert len(doc.source_signals) == 1
    assert doc.source_signals[0].signal_type == "criteria_changed"
    assert doc.source_signals[0].source_family == "issue_tracker"


def test_parse_issue_number() -> None:
    assert _parse_issue_number("#42") == 42
    assert _parse_issue_number("42") == 42
    assert _parse_issue_number("abc") is None


def test_build_detail_state_changed() -> None:
    detail = _build_detail("#42", "closed", (), ("state_changed",))
    assert "state is now closed" in detail


def test_build_detail_labels_changed() -> None:
    detail = _build_detail("#42", "open", ("bug", "critical"), ("labels_changed",))
    assert "bug" in detail
    assert "critical" in detail


def test_build_detail_multiple_kinds() -> None:
    detail = _build_detail("#42", "closed", ("bug",), ("state_changed", "labels_changed"))
    assert "state is now closed" in detail
    assert "bug" in detail
