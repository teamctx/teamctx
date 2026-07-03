from __future__ import annotations

from teamctx.assessment import assess
from teamctx.connectors._contract import metadata_only_policy, source_status
from teamctx.core.broker import broker_answer
from teamctx.core.contracts import RequestContext, SourceSignal, SourceStatus


def _request(paths=("src/app.py",)) -> RequestContext:
    return RequestContext(
        schema_version="teamctx.request_context.v0", request_id="t", repo="acme/widgets",
        branch="feature", task="work", paths=list(paths), linked_issues=[],
        requested_at="2026-06-28T00:00:00Z", requesting_principal=None,
    )


def _collision_signal() -> SourceSignal:
    return SourceSignal(
        schema_version="teamctx.source_signal.v0", id="sig_pr_7", signal_type="collision",
        source_family="git_hosting", scope={"repo": "acme/widgets", "files": ["src/app.py"]},
        evidence_summary="PR #7 changes src/app.py", source_display="github acme/widgets#7",
        freshness="fresh", confidence="high", visibility="visible",
        created_at="2026-06-28T00:00:00Z", observed_at="2026-06-28T00:00:00Z",
        expires_at="next_refresh", policy=metadata_only_policy("pr metadata is evidence"),
    )


def _fresh_status(family: str) -> SourceStatus:
    return source_status(
        source_id=f"{family}-probe", source_family=family, scope={"repo": "acme/widgets"},
        status="fresh", observed_at="2026-06-28T00:00:00Z", safe_user_message="checked",
        visibility="silent", policy_reason="status only",
    )


def _unavailable_status(family: str) -> SourceStatus:
    return source_status(
        source_id=f"{family}-probe", source_family=family, scope={"repo": "acme/widgets"},
        status="unavailable", observed_at="2026-06-28T00:00:00Z", safe_user_message="no access",
        visibility="silent", policy_reason="status only",
    )


def _pending_status(family: str) -> SourceStatus:
    return source_status(
        source_id=f"{family}-probe", source_family=family, scope={"repo": "acme/widgets"},
        status="pending", observed_at="2026-06-28T00:00:00Z",
        safe_user_message="checks still running", visibility="warning_when_relevant",
        policy_reason="status only",
    )


def _disabled_status(family: str, message: str) -> SourceStatus:
    return source_status(
        source_id=f"{family}-probe",
        source_family=family,
        scope={"repo": "acme/widgets"},
        status="disabled",
        observed_at="2026-06-28T00:00:00Z",
        safe_user_message=message,
        visibility="warning_when_relevant",
        policy_reason="status only",
    )


def test_status_for_maps_the_new_carrier_reasons() -> None:
    from teamctx.assessment import _status_for
    from teamctx.core.evaluate import Valuation

    assert _status_for(Valuation("unknown", "incomplete[pending]")) == "pending"
    assert _status_for(Valuation("unknown", "not_applicable[out-of-scope]")) == "not_applicable"


def test_pending_important_gate_is_cant_verify() -> None:
    # a gate whose checks are still running cannot be asserted green, so it reads cant_verify,
    # exactly like an unreachable important source. Only the gate can be pending today.
    a = assess(broker_answer(_request(), [], [_pending_status("ci_deploy")]))
    assert a.kind == "cant_verify"
    assert next(c for c in a.checks if c.check == "gate").status == "pending"


def test_found_is_heads_up_and_card_grouped_to_conflict() -> None:
    a = assess(broker_answer(_request(), [_collision_signal()], [_fresh_status("git_hosting")]))
    assert a.kind == "heads_up"
    conflict = next(c for c in a.checks if c.check == "conflict")
    assert conflict.status == "found"
    assert len(conflict.cards) == 1
    assert len(a.findings) == 1


def test_unreachable_important_is_cant_verify() -> None:
    a = assess(broker_answer(_request(), [], [_unavailable_status("git_hosting")]))
    assert a.kind == "cant_verify"
    assert next(c for c in a.checks if c.check == "conflict").status == "unreachable"


def test_clear_important_with_only_policy_gaps_is_ready() -> None:
    a = assess(broker_answer(_request(), [], [_fresh_status("git_hosting")]))
    assert a.kind == "ready"
    assert next(c for c in a.checks if c.check == "conflict").status == "clear"
    assert next(c for c in a.checks if c.check == "criteria").status == "not_configured"


def test_checks_are_ordered_conflict_criteria_docs_gate() -> None:
    a = assess(broker_answer(_request(), [], [_fresh_status("git_hosting")]))
    assert [c.check for c in a.checks] == ["conflict", "criteria", "docs", "gate"]


def test_conflicting_evidence_is_a_finding() -> None:
    from teamctx.assessment import _status_for
    from teamctx.core.evaluate import Valuation

    assert _status_for(Valuation("unknown", "conflicting-evidence")) == "found"


def test_unreachable_non_important_check_stays_ready() -> None:
    # git_hosting fresh -> conflict clear; docs unavailable -> docs unreachable but NOT important,
    # so the kind stays ready (only conflict/gate unreachable triggers cant_verify).
    a = assess(
        broker_answer(_request(), [], [_fresh_status("git_hosting"), _unavailable_status("docs")])
    )
    assert a.kind == "ready"
    assert next(c for c in a.checks if c.check == "docs").status == "unreachable"


def test_disabled_status_note_routes_to_matching_check() -> None:
    note = (
        "spec changes (no issue could be derived from your branch or commits; name one "
        "with --issue)"
    )

    a = assess(broker_answer(_request(), [], [_disabled_status("issue_tracker", note)]))

    criteria = next(c for c in a.checks if c.check == "criteria")
    docs = next(c for c in a.checks if c.check == "docs")
    assert criteria.status == "not_configured"
    assert criteria.note == note
    assert docs.note is None
