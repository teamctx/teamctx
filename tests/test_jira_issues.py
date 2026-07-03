import json
from urllib.error import HTTPError

from teamctx.connectors.jira import run_jira_issues_probe
from teamctx.core.contracts import RequestContext

OBSERVED = "2026-07-03T12:00:00Z"
SINCE = "2026-07-01T12:00:00Z"
BASE_URL = "https://jira.example.test"


def _request(linked: list[str] | None = None) -> RequestContext:
    return RequestContext(
        schema_version="teamctx.request_context.v0",
        request_id="test",
        repo="teamctx/teamctx",
        task="test",
        paths=["src/teamctx/cli.py"],
        linked_issues=linked or ["PROJ-123"],
        requested_at=OBSERVED,
        requesting_principal=None,
    )


class _FakeResponse:
    def __init__(self, data: object) -> None:
        self._data = data

    def read(self) -> bytes:
        return json.dumps(self._data).encode()

    def __enter__(self):
        return self

    def __exit__(self, *a):
        pass


def _fake_opener(responses: dict[str, object]):
    requests = []

    def opener(request):
        requests.append(request)
        url = request.full_url
        best_pattern = ""
        best_data: object = {}
        for pattern, data in responses.items():
            if pattern in url and len(pattern) > len(best_pattern):
                best_pattern = pattern
                best_data = data
        if isinstance(best_data, BaseException):
            raise best_data
        return _FakeResponse(best_data)

    opener.requests = requests
    return opener


def _http_error(status: int) -> HTTPError:
    return HTTPError("https://jira.example.test", status, "boom", hdrs=None, fp=None)


def _issue_payload(
    *,
    key: str = "PROJ-123",
    updated: object = "2026-07-02T10:00:00.000+0000",
    summary: object = "Acceptance criteria",
    status: object = "In Progress",
    labels: object = ("backend",),
) -> dict:
    return {
        "key": key,
        "fields": {
            "summary": summary,
            "status": {"name": status},
            "labels": list(labels) if isinstance(labels, tuple) else labels,
            "updated": updated,
        },
    }


def _changelog_payload(*, is_last: object = True, items: list[dict] | None = None) -> dict:
    return {
        "isLast": is_last,
        "values": [
            {
                "created": "2026-07-02T09:00:00.000+0000",
                "items": items if items is not None else [{"field": "description"}],
            }
        ],
    }


def test_probe_without_auth_returns_verbatim_no_credential_copy() -> None:
    doc = run_jira_issues_probe(
        base_url=BASE_URL,
        issues=["PROJ-123"],
        since=SINCE,
        auth=None,
        request_context=_request(),
        observed_at=OBSERVED,
        opener=_fake_opener({}),
    )

    assert doc.source_statuses[0].source_id == "jira_issues"
    assert doc.source_statuses[0].status == "unavailable"
    assert doc.source_statuses[0].safe_user_message == (
        "Jira is configured but no Atlassian credential was found. Set ATLASSIAN_EMAIL and "
        "ATLASSIAN_API_TOKEN (or ATLASSIAN_API_TOKEN_FILE)."
    )
    assert doc.source_signals == []


def test_probe_with_no_issues_returns_fresh_empty() -> None:
    doc = run_jira_issues_probe(
        base_url=BASE_URL,
        issues=[],
        since=SINCE,
        auth=("person@example.com", "token"),
        request_context=_request([]),
        observed_at=OBSERVED,
        opener=_fake_opener({}),
    )

    assert doc.source_statuses[0].source_id == "jira_issues"
    assert doc.source_statuses[0].status == "fresh"
    assert doc.source_signals == []


def test_probe_fetches_jira_issue_with_basic_auth_and_detects_description_change() -> None:
    opener = _fake_opener(
        {
            "/rest/api/3/issue/PROJ-123?fields=summary,status,labels,updated": _issue_payload(),
            "/rest/api/3/issue/PROJ-123/changelog?maxResults=100": _changelog_payload(),
        }
    )

    doc = run_jira_issues_probe(
        base_url=f"{BASE_URL}/",
        issues=["PROJ-123"],
        since=SINCE,
        auth=("person@example.com", "token"),
        request_context=_request(),
        observed_at=OBSERVED,
        opener=opener,
    )

    assert len(doc.source_signals) == 1
    signal = doc.source_signals[0]
    assert signal.source_display == "Jira PROJ-123: Acceptance criteria"
    assert signal.scope["issue"] == "PROJ-123"
    assert signal.scope["url"] == f"{BASE_URL}/browse/PROJ-123"
    assert signal.scope["state"] == "In Progress"
    assert signal.scope["labels"] == ["backend"]
    assert signal.scope["change_kinds"] == ["body_edited"]
    assert "description" in signal.evidence_summary
    assert doc.source_statuses[0].status == "fresh"
    assert [request.full_url for request in opener.requests] == [
        f"{BASE_URL}/rest/api/3/issue/PROJ-123?fields=summary,status,labels,updated",
        f"{BASE_URL}/rest/api/3/issue/PROJ-123/changelog?maxResults=100",
    ]
    assert opener.requests[0].get_header("Accept") == "application/json"
    assert opener.requests[0].get_header("Authorization", "").startswith("Basic ")


def test_probe_detects_status_and_label_changes() -> None:
    opener = _fake_opener(
        {
            "/rest/api/3/issue/PROJ-123?fields=summary,status,labels,updated": _issue_payload(
                status="Done", labels=("done", "release")
            ),
            "/rest/api/3/issue/PROJ-123/changelog?maxResults=100": _changelog_payload(
                items=[{"field": "status"}, {"field": "labels"}]
            ),
        }
    )

    doc = run_jira_issues_probe(
        base_url=BASE_URL,
        issues=["PROJ-123"],
        since=SINCE,
        auth=("person@example.com", "token"),
        request_context=_request(),
        observed_at=OBSERVED,
        opener=opener,
    )

    assert doc.source_signals[0].scope["change_kinds"] == ["state_changed", "labels_changed"]
    assert "status is now Done" in doc.source_signals[0].evidence_summary
    assert "labels now: done, release" in doc.source_signals[0].evidence_summary


def test_probe_uses_body_fallback_for_other_fields_when_issue_updated() -> None:
    opener = _fake_opener(
        {
            "/rest/api/3/issue/PROJ-123?fields=summary,status,labels,updated": _issue_payload(),
            "/rest/api/3/issue/PROJ-123/changelog?maxResults=100": _changelog_payload(
                items=[{"field": "customfield_10010"}]
            ),
        }
    )

    doc = run_jira_issues_probe(
        base_url=BASE_URL,
        issues=["PROJ-123"],
        since=SINCE,
        auth=("person@example.com", "token"),
        request_context=_request(),
        observed_at=OBSERVED,
        opener=opener,
    )

    assert doc.source_signals[0].scope["change_kinds"] == ["body_edited"]


def test_probe_skips_unchanged_issue() -> None:
    opener = _fake_opener(
        {
            "/rest/api/3/issue/PROJ-123?fields=summary,status,labels,updated": _issue_payload(
                updated="2026-06-30T10:00:00.000+0000"
            ),
        }
    )

    doc = run_jira_issues_probe(
        base_url=BASE_URL,
        issues=["PROJ-123"],
        since=SINCE,
        auth=("person@example.com", "token"),
        request_context=_request(),
        observed_at=OBSERVED,
        opener=opener,
    )

    assert doc.source_signals == []
    assert doc.source_statuses[0].status == "fresh"
    assert len(opener.requests) == 1


def test_missing_updated_is_stale_with_verbatim_copy() -> None:
    opener = _fake_opener(
        {
            "/rest/api/3/issue/PROJ-123?fields=summary,status,labels,updated": _issue_payload(
                updated=None
            ),
        }
    )

    doc = run_jira_issues_probe(
        base_url=BASE_URL,
        issues=["PROJ-123"],
        since=SINCE,
        auth=("person@example.com", "token"),
        request_context=_request(),
        observed_at=OBSERVED,
        opener=opener,
    )

    assert doc.source_statuses[0].status == "stale"
    assert doc.source_statuses[0].safe_user_message == (
        "Jira returned an unreadable update time for PROJ-123; its criteria state can't be "
        "confirmed."
    )
    assert doc.source_signals == []


def test_unparseable_updated_is_stale_with_verbatim_copy() -> None:
    opener = _fake_opener(
        {
            "/rest/api/3/issue/PROJ-123?fields=summary,status,labels,updated": _issue_payload(
                updated="not-a-time"
            ),
        }
    )

    doc = run_jira_issues_probe(
        base_url=BASE_URL,
        issues=["PROJ-123"],
        since=SINCE,
        auth=("person@example.com", "token"),
        request_context=_request(),
        observed_at=OBSERVED,
        opener=opener,
    )

    assert doc.source_statuses[0].status == "stale"
    assert doc.source_statuses[0].safe_user_message == (
        "Jira returned an unreadable update time for PROJ-123; its criteria state can't be "
        "confirmed."
    )


def test_changelog_fetch_failure_on_known_changed_issue_still_fires_signal() -> None:
    opener = _fake_opener(
        {
            "/rest/api/3/issue/PROJ-123?fields=summary,status,labels,updated": _issue_payload(),
            "/rest/api/3/issue/PROJ-123/changelog?maxResults=100": _http_error(500),
        }
    )

    doc = run_jira_issues_probe(
        base_url=BASE_URL,
        issues=["PROJ-123"],
        since=SINCE,
        auth=("person@example.com", "token"),
        request_context=_request(),
        observed_at=OBSERVED,
        opener=opener,
    )

    assert doc.source_statuses[0].status == "fresh"
    assert doc.source_signals[0].scope["change_kinds"] == ["body_edited"]
    assert "changelog details unavailable" in doc.source_signals[0].evidence_summary


def test_absent_is_last_is_treated_as_truncated_and_stale() -> None:
    opener = _fake_opener(
        {
            "/rest/api/3/issue/PROJ-123?fields=summary,status,labels,updated": _issue_payload(),
            "/rest/api/3/issue/PROJ-123/changelog?maxResults=100": {
                "values": [{"created": "2026-07-02T09:00:00.000+0000", "items": []}],
            },
        }
    )

    doc = run_jira_issues_probe(
        base_url=BASE_URL,
        issues=["PROJ-123"],
        since=SINCE,
        auth=("person@example.com", "token"),
        request_context=_request(),
        observed_at=OBSERVED,
        opener=opener,
    )

    assert doc.source_statuses[0].status == "stale"
    assert doc.source_statuses[0].safe_user_message == (
        "Checked the most recent 100 changes on PROJ-123; more history exists, so this is "
        "not a complete check."
    )


def test_malformed_is_last_is_treated_as_truncated_and_stale() -> None:
    opener = _fake_opener(
        {
            "/rest/api/3/issue/PROJ-123?fields=summary,status,labels,updated": _issue_payload(),
            "/rest/api/3/issue/PROJ-123/changelog?maxResults=100": _changelog_payload(
                is_last="yes"
            ),
        }
    )

    doc = run_jira_issues_probe(
        base_url=BASE_URL,
        issues=["PROJ-123"],
        since=SINCE,
        auth=("person@example.com", "token"),
        request_context=_request(),
        observed_at=OBSERVED,
        opener=opener,
    )

    assert doc.source_statuses[0].status == "stale"
    assert doc.source_statuses[0].safe_user_message == (
        "Checked the most recent 100 changes on PROJ-123; more history exists, so this is "
        "not a complete check."
    )


def test_issue_fetch_unauthorized_is_unavailable_with_current_access() -> None:
    opener = _fake_opener(
        {
            "/rest/api/3/issue/PROJ-123?fields=summary,status,labels,updated": _http_error(401),
        }
    )

    doc = run_jira_issues_probe(
        base_url=BASE_URL,
        issues=["PROJ-123"],
        since=SINCE,
        auth=("person@example.com", "token"),
        request_context=_request(),
        observed_at=OBSERVED,
        opener=opener,
    )

    assert doc.source_statuses[0].status == "unavailable"
    assert doc.source_statuses[0].safe_user_message == "Jira is unavailable with current access."
