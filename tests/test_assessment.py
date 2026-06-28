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
