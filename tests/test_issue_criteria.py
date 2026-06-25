from teamctx.connectors.issue_criteria import (
    IssueCriteriaChange,
    normalize_issue_changes,
    unavailable_issues_document,
)
from teamctx.core.contracts import RequestContext

OBSERVED = "2026-06-25T12:00:00Z"


def _request() -> RequestContext:
    return RequestContext(
        schema_version="teamctx.request_context.v0",
        request_id="test",
        repo="teamctx/teamctx",
        task="test",
        paths=["src/teamctx/cli.py"],
        linked_issues=["#42", "#99"],
        requested_at=OBSERVED,
        requesting_principal=None,
    )


def test_normalize_emits_criteria_changed_signal() -> None:
    change = IssueCriteriaChange(
        repo="teamctx/teamctx",
        issue="#42",
        issue_url="https://github.com/teamctx/teamctx/issues/42",
        title="Add widget support",
        state="open",
        labels=("enhancement",),
        change_kinds=("body_edited",),
        detail="Issue #42 updated: description or comments updated.",
        updated_at="2026-06-25T11:00:00Z",
    )
    doc = normalize_issue_changes(_request(), [change], observed_at=OBSERVED)
    assert len(doc.source_signals) == 1
    sig = doc.source_signals[0]
    assert sig.signal_type == "criteria_changed"
    assert sig.source_family == "issue_tracker"
    assert sig.scope["issue"] == "#42"
    assert sig.scope["state"] == "open"
    assert sig.scope["change_kinds"] == ["body_edited"]
    assert sig.scope["labels"] == ["enhancement"]
    assert "Issue #42" in sig.evidence_summary


def test_normalize_multiple_changes() -> None:
    changes = [
        IssueCriteriaChange(
            repo="teamctx/teamctx", issue="#42",
            issue_url="https://github.com/teamctx/teamctx/issues/42",
            title="Add widget", state="closed", labels=(),
            change_kinds=("state_changed",),
            detail="Issue #42 updated: state is now closed.",
            updated_at="2026-06-25T11:00:00Z",
        ),
        IssueCriteriaChange(
            repo="teamctx/teamctx", issue="#99",
            issue_url="https://github.com/teamctx/teamctx/issues/99",
            title="Fix bug", state="open", labels=("bug",),
            change_kinds=("labels_changed",),
            detail="Issue #99 updated: labels now: bug.",
            updated_at="2026-06-25T11:30:00Z",
        ),
    ]
    doc = normalize_issue_changes(_request(), changes, observed_at=OBSERVED)
    assert len(doc.source_signals) == 2
    assert doc.source_signals[0].scope["issue"] == "#42"
    assert doc.source_signals[1].scope["issue"] == "#99"


def test_normalize_no_changes_produces_empty_signals() -> None:
    doc = normalize_issue_changes(_request(), [], observed_at=OBSERVED)
    assert len(doc.source_signals) == 0
    assert len(doc.source_statuses) == 1
    assert doc.source_statuses[0].status == "fresh"
    assert doc.source_statuses[0].source_family == "issue_tracker"


def test_normalize_omits_labels_from_scope_when_empty() -> None:
    change = IssueCriteriaChange(
        repo="teamctx/teamctx", issue="#42",
        issue_url="https://github.com/teamctx/teamctx/issues/42",
        title="Add widget", state="open", labels=(),
        change_kinds=("body_edited",),
        detail="Issue #42 updated: description or comments updated.",
        updated_at="2026-06-25T11:00:00Z",
    )
    doc = normalize_issue_changes(_request(), [change], observed_at=OBSERVED)
    assert "labels" not in doc.source_signals[0].scope


def test_unavailable_document_reports_issue_tracker() -> None:
    doc = unavailable_issues_document(
        _request(),
        repo="teamctx/teamctx",
        observed_at=OBSERVED,
        safe_user_message="No token.",
    )
    assert len(doc.source_signals) == 0
    assert doc.source_statuses[0].status == "unavailable"
    assert doc.source_statuses[0].source_family == "issue_tracker"
