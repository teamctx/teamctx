from __future__ import annotations

from collections.abc import Callable

import pytest

from teamctx.core.authority import AuthorityEntry
from teamctx.core.content_digest import content_digest
from teamctx.core.contracts import (
    ClosureEntry,
    ClosureLike,
    ClosureProjection,
    PolicyDecision,
    SourceSignal,
    SourceStatus,
)

OBSERVED = "2026-07-04T12:00:00Z"


def _policy(reason: str = "test") -> PolicyDecision:
    return PolicyDecision(
        schema_version="teamctx.policy_decision.v0",
        can_render_to_user=True,
        can_render_to_agent=True,
        can_include_source_text=False,
        requires_review_for_guidance=False,
        decision_reason=reason,
    )


def _signal(**overrides: object) -> SourceSignal:
    data: dict[str, object] = {
        "schema_version": "teamctx.source_signal.v0",
        "id": "sig-1",
        "signal_type": "collision",
        "source_family": "git_hosting",
        "scope": {"repo": "acme/widgets", "files": ["src/app.py"]},
        "evidence_summary": "Open PR #7 changed src/app.py.",
        "source_display": "GitHub PR #7",
        "freshness": "fresh",
        "confidence": "high",
        "visibility": "visible",
        "created_at": OBSERVED,
        "observed_at": OBSERVED,
        "expires_at": "next_refresh",
        "policy": _policy(),
    }
    data.update(overrides)
    return SourceSignal.model_validate(data)


def _changed_since_start_signal() -> SourceSignal:
    return _signal(
        id="delta-1",
        signal_type="changed_since_start",
        evidence_summary="PR #7 appeared since you started.",
    )


def _status(**overrides: object) -> SourceStatus:
    data: dict[str, object] = {
        "schema_version": "teamctx.source_status.v0",
        "source_id": "github_pr_metadata",
        "source_family": "git_hosting",
        "scope": {"repo": "acme/widgets"},
        "status": "fresh",
        "last_checked_at": OBSERVED,
        "safe_user_message": "checked",
        "normal_context_visibility": "silent",
        "policy": _policy(),
    }
    data.update(overrides)
    return SourceStatus.model_validate(data)


def _digest(
    *,
    signals: tuple[SourceSignal, ...] = (_signal(),),
    statuses: tuple[SourceStatus, ...] = (_status(),),
    closure: tuple[ClosureLike, ...] = (
        ClosureProjection(proposition="no_pr_conflicts_with_paths", status="complete"),
    ),
    authority: tuple[AuthorityEntry, ...] = (
        AuthorityEntry(subject="rounding-cap", state="resolved", value="5"),
    ),
) -> str:
    return content_digest(signals, statuses, closure, authority)


@pytest.mark.parametrize(
    ("field", "value"),
    [
        ("signal_type", "missed_gate"),
        ("source_family", "ci_deploy"),
        ("scope", {"repo": "acme/widgets", "files": ["src/other.py"]}),
        ("evidence_summary", "Branch check failed."),
        ("source_display", "GitHub check run"),
        ("freshness", "stale"),
        ("confidence", "medium"),
        ("visibility", "warning_only"),
    ],
)
def test_signal_included_fields_change_digest(field: str, value: object) -> None:
    assert _digest() != _digest(signals=(_signal(**{field: value}),))


@pytest.mark.parametrize(
    ("field", "value"),
    [
        ("id", "sig-2"),
        ("created_at", "2026-07-04T12:01:00Z"),
        ("observed_at", "2026-07-04T12:01:00Z"),
        ("expires_at", "2026-07-04T12:02:00Z"),
        ("policy", _policy("different policy reason")),
    ],
)
def test_signal_excluded_fields_do_not_change_digest(field: str, value: object) -> None:
    assert _digest() == _digest(signals=(_signal(**{field: value}),))


def test_changed_since_start_signals_are_excluded() -> None:
    assert _digest() == _digest(signals=(_signal(), _changed_since_start_signal()))


@pytest.mark.parametrize(
    ("field", "value"),
    [
        ("source_id", "github_check_runs"),
        ("source_family", "ci_deploy"),
        ("status", "unavailable"),
        ("normal_context_visibility", "always"),
    ],
)
def test_status_included_fields_change_digest(field: str, value: object) -> None:
    assert _digest() != _digest(statuses=(_status(**{field: value}),))


@pytest.mark.parametrize(
    ("field", "value"),
    [
        ("scope", {"repo": "other/widgets"}),
        ("last_checked_at", "2026-07-04T12:01:00Z"),
        ("safe_user_message", "checked a different page of results"),
        ("policy", _policy("different status policy")),
    ],
)
def test_status_excluded_fields_do_not_change_digest(field: str, value: object) -> None:
    assert _digest() == _digest(statuses=(_status(**{field: value}),))


@pytest.mark.parametrize(
    "mutate",
    [
        lambda entry: ClosureProjection(proposition="all_gates_pass", status=entry.status),
        lambda entry: ClosureProjection(
            proposition=entry.proposition, status="incomplete[stale-dep]"
        ),
    ],
)
def test_closure_included_fields_change_digest(
    mutate: Callable[[ClosureProjection], ClosureProjection],
) -> None:
    entry = ClosureProjection(proposition="no_pr_conflicts_with_paths", status="complete")
    assert _digest(closure=(entry,)) != _digest(closure=(mutate(entry),))


def test_closure_rich_fields_do_not_change_digest() -> None:
    entry = ClosureEntry(
        check_id="conflict",
        proposition="no_pr_conflicts_with_paths",
        consumed_document_ids=("doc-b", "doc-a"),
        closure_status="complete",
        reason="git hosting source was fresh",
    )
    changed = ClosureEntry(
        check_id="different-check",
        proposition=entry.proposition,
        consumed_document_ids=("doc-z",),
        closure_status=entry.status,
        reason="different reason",
    )

    assert entry.consumed_document_ids == ("doc-a", "doc-b")
    assert _digest(closure=(entry,)) == _digest(closure=(changed,))


@pytest.mark.parametrize(
    "mutate",
    [
        lambda entry: AuthorityEntry(subject="different", state=entry.state, value=entry.value),
        lambda entry: AuthorityEntry(subject=entry.subject, state="conflicted", value=entry.value),
        lambda entry: AuthorityEntry(subject=entry.subject, state=entry.state, value="10"),
    ],
)
def test_authority_included_fields_change_digest(
    mutate: Callable[[AuthorityEntry], AuthorityEntry],
) -> None:
    entry = AuthorityEntry(subject="rounding-cap", state="resolved", value="5")
    assert _digest(authority=(entry,)) != _digest(authority=(mutate(entry),))


def test_item_order_does_not_change_digest() -> None:
    signals = (_signal(id="b", source_display="GitHub PR #2"), _signal(id="a"))
    statuses = (_status(source_id="b"), _status(source_id="a"))
    closure = (
        ClosureProjection(proposition="all_gates_pass", status="complete"),
        ClosureProjection(proposition="no_pr_conflicts_with_paths", status="complete"),
    )
    authority = (
        AuthorityEntry(subject="b", state="missing", value=None),
        AuthorityEntry(subject="a", state="resolved", value="1"),
    )

    assert _digest(signals=signals, statuses=statuses, closure=closure, authority=authority) == (
        _digest(
            signals=tuple(reversed(signals)),
            statuses=tuple(reversed(statuses)),
            closure=tuple(reversed(closure)),
            authority=tuple(reversed(authority)),
        )
    )
