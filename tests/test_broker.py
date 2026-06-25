"""Tests for the broker entry point + compose seam (Phase 1 of foundation hardening)."""

from __future__ import annotations

from teamctx.core.broker import (
    BrokerAnswer,
    broker_answer,
    broker_answer_from_documents,
    compose,
)
from teamctx.core.contracts import (
    CoreContractDocument,
    PolicyDecision,
    RequestContext,
    SourceSignal,
    SourceStatus,
)

OBSERVED = "2026-06-25T12:00:00Z"


def _request(paths: list[str] | None = None) -> RequestContext:
    return RequestContext(
        schema_version="teamctx.request_context.v0",
        request_id="test",
        repo="teamctx/teamctx",
        task="test",
        paths=paths or ["src/teamctx/cli.py"],
        linked_issues=[],
        requested_at=OBSERVED,
        requesting_principal=None,
    )


def _policy() -> PolicyDecision:
    return PolicyDecision(
        schema_version="teamctx.policy_decision.v0",
        can_render_to_user=True,
        can_render_to_agent=True,
        can_include_source_text=False,
        requires_review_for_guidance=False,
        decision_reason="test",
    )


def _collision_signal(index: int) -> SourceSignal:
    return SourceSignal(
        schema_version="teamctx.source_signal.v0",
        id=f"sig_collision_{index}",
        signal_type="collision",
        source_family="git_hosting",
        scope={"repo": "teamctx/teamctx", "files": ["src/teamctx/cli.py"]},
        evidence_summary=f"Open PR #{index} changed src/teamctx/cli.py.",
        source_display=f"GitHub PR #{index}",
        freshness="fresh",
        confidence="high",
        visibility="visible",
        created_at=OBSERVED,
        observed_at=OBSERVED,
        expires_at="next_refresh",
        policy=_policy(),
    )


def _status(source_id: str, family: str) -> SourceStatus:
    return SourceStatus(
        schema_version="teamctx.source_status.v0",
        source_id=source_id,
        source_family=family,
        scope={"repo": "teamctx/teamctx"},
        status="fresh",
        last_checked_at=OBSERVED,
        safe_user_message="refreshed",
        normal_context_visibility="silent",
        policy=_policy(),
    )


def _document(signals: list[SourceSignal], statuses: list[SourceStatus]) -> CoreContractDocument:
    return CoreContractDocument(
        schema_version="teamctx.core_contract_document.v0",
        request_context=_request(),
        source_signals=signals,
        source_statuses=statuses,
        source_open_targets=[],
        guidance_records=[],
        session_context_uses=[],
        context_cards=[],
    )


def test_compose_unions_signals_and_statuses() -> None:
    doc_a = _document([_collision_signal(1)], [_status("github_pr_metadata", "git_hosting")])
    doc_b = _document([], [_status("github_check_runs", "ci_deploy")])
    composed = compose([doc_a, doc_b])
    assert len(composed.signals) == 1
    assert len(composed.statuses) == 2
    assert {s.source_id for s in composed.statuses} == {"github_pr_metadata", "github_check_runs"}


def test_compose_empty_is_empty() -> None:
    composed = compose([])
    assert composed.signals == ()
    assert composed.statuses == ()
    assert composed.open_targets == ()
    assert composed.guidance_records == ()


def test_compose_preserves_order() -> None:
    doc_a = _document([_collision_signal(1)], [])
    doc_b = _document([_collision_signal(2)], [])
    composed = compose([doc_a, doc_b])
    assert [s.id for s in composed.signals] == ["sig_collision_1", "sig_collision_2"]


def test_broker_answer_returns_selection_and_one_verdict_per_kind() -> None:
    answer = broker_answer(
        _request(),
        [_collision_signal(1)],
        [_status("github_pr_metadata", "git_hosting")],
    )
    assert isinstance(answer, BrokerAnswer)
    # one verdict per registered card kind
    assert len(answer.verdicts) == 4
    labels = [label for label, _ in answer.verdicts]
    assert labels == ["Conflict check", "Criteria check", "Docs check", "Gate check"]


def test_broker_answer_conflict_is_false_when_collision_present() -> None:
    answer = broker_answer(
        _request(),
        [_collision_signal(1)],
        [_status("github_pr_metadata", "git_hosting")],
    )
    verdicts = dict(answer.verdicts)
    assert verdicts["Conflict check"].value == "false"  # a collision refutes "no conflict"
    # a derived collision card is present
    assert any(card.section == "Needs attention" for card in answer.selection.cards)


def test_broker_answer_conflict_is_true_when_clear_and_complete() -> None:
    answer = broker_answer(
        _request(),
        [],  # no collisions
        [_status("github_pr_metadata", "git_hosting")],  # git_hosting observed fresh
    )
    verdicts = dict(answer.verdicts)
    assert verdicts["Conflict check"].value == "true"  # clear + complete coverage
    # but a source we did NOT check stays Unknown (absence is not all-clear)
    assert verdicts["Gate check"].value == "unknown"


def test_broker_answer_from_documents_composes_then_answers() -> None:
    doc_a = _document([_collision_signal(1)], [_status("github_pr_metadata", "git_hosting")])
    doc_b = _document([], [_status("github_check_runs", "ci_deploy")])
    answer = broker_answer_from_documents(_request(), [doc_a, doc_b])
    verdicts = dict(answer.verdicts)
    # collision from doc_a refutes conflict; gate coverage from doc_b is now complete + clear
    assert verdicts["Conflict check"].value == "false"
    assert verdicts["Gate check"].value == "true"
