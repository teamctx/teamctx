"""Tests for the broker entry point + compose seam (Phase 1 of foundation hardening)."""

from __future__ import annotations

import pytest

from teamctx.contract_render import render_broker_answer
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


def _document(
    signals: list[SourceSignal],
    statuses: list[SourceStatus],
    *,
    document_id: str = "doc_test",
    document_type: str = "forge_review",
) -> CoreContractDocument:
    return CoreContractDocument(
        schema_version="teamctx.core_contract_document.v0",
        document_id=document_id,
        document_type=document_type,
        request_context=_request(),
        source_signals=signals,
        source_statuses=statuses,
        source_open_targets=[],
        guidance_records=[],
        session_context_uses=[],
        context_cards=[],
    )


def test_compose_unions_signals_and_statuses() -> None:
    doc_a = _document(
        [_collision_signal(1)],
        [_status("github_pr_metadata", "git_hosting")],
        document_id="doc_github_pr_metadata",
        document_type="forge_review",
    )
    doc_b = _document(
        [],
        [_status("github_check_runs", "ci_deploy")],
        document_id="doc_github_check_runs",
        document_type="gate_status",
    )
    composed = compose([doc_a, doc_b])
    assert len(composed.signals) == 1
    assert len(composed.statuses) == 2
    assert [doc.document_id for doc in composed.documents] == [
        "doc_github_pr_metadata",
        "doc_github_check_runs",
    ]
    assert {s.source_id for s in composed.statuses} == {"github_pr_metadata", "github_check_runs"}


def test_compose_empty_is_empty() -> None:
    composed = compose([])
    assert composed.signals == ()
    assert composed.statuses == ()
    assert composed.open_targets == ()
    assert composed.guidance_records == ()
    assert composed.documents == ()


def test_compose_preserves_order() -> None:
    doc_a = _document([_collision_signal(1)], [], document_id="doc_a")
    doc_b = _document([_collision_signal(2)], [], document_id="doc_b")
    composed = compose([doc_a, doc_b])
    assert [s.id for s in composed.signals] == ["sig_collision_1", "sig_collision_2"]


def test_compose_rejects_duplicate_document_ids() -> None:
    doc_a = _document([], [], document_id="doc_duplicate")
    doc_b = _document([], [], document_id="doc_duplicate")

    with pytest.raises(ValueError, match="duplicate document id: doc_duplicate"):
        compose([doc_a, doc_b])


def test_broker_answer_returns_selection_and_one_verdict_per_kind() -> None:
    signal = _collision_signal(1)
    status = _status("github_pr_metadata", "git_hosting")
    request = _request()
    answer = broker_answer(
        request,
        [signal],
        [status],
    )
    assert isinstance(answer, BrokerAnswer)
    assert answer.request == request
    assert answer.source_signals == (signal,)
    assert answer.source_statuses == (status,)
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
    doc_a = _document(
        [_collision_signal(1)],
        [_status("github_pr_metadata", "git_hosting")],
        document_id="doc_github_pr_metadata",
        document_type="forge_review",
    )
    doc_b = _document(
        [],
        [_status("github_check_runs", "ci_deploy")],
        document_id="doc_github_check_runs",
        document_type="gate_status",
    )
    request = _request()
    answer = broker_answer_from_documents(request, [doc_a, doc_b])
    verdicts = dict(answer.verdicts)
    assert answer.request == request
    # collision from doc_a refutes conflict; gate coverage from doc_b is now complete + clear
    assert verdicts["Conflict check"].value == "false"
    assert verdicts["Gate check"].value == "true"
    closure_by_check = {entry.check_id: entry for entry in answer.selection.closure}
    assert closure_by_check["conflict"].consumed_document_ids == ("doc_github_pr_metadata",)
    assert closure_by_check["gate"].consumed_document_ids == ("doc_github_check_runs",)


def test_broker_answer_from_documents_sorts_consumed_document_ids() -> None:
    doc_b = _document(
        [],
        [_status("gitlab_mr_metadata", "git_hosting")],
        document_id="doc_z_gitlab_mr_metadata",
    )
    doc_a = _document(
        [],
        [_status("github_pr_metadata", "git_hosting")],
        document_id="doc_a_github_pr_metadata",
    )

    answer = broker_answer_from_documents(_request(), [doc_b, doc_a])

    conflict = next(entry for entry in answer.selection.closure if entry.check_id == "conflict")
    assert conflict.consumed_document_ids == (
        "doc_a_github_pr_metadata",
        "doc_z_gitlab_mr_metadata",
    )


def test_document_identity_does_not_touch_snapshot_digest_or_rendered_bytes() -> None:
    request = _request()
    status = _status("github_pr_metadata", "git_hosting")
    base_doc = _document([], [status], document_id="doc_github_pr_metadata")
    renamed_doc = _document([], [status], document_id="doc_renamed_same_status")

    base = broker_answer_from_documents(request, [base_doc])
    renamed = broker_answer_from_documents(request, [renamed_doc])

    assert base.selection.snapshot_digest == renamed.selection.snapshot_digest
    assert render_broker_answer(base) == render_broker_answer(renamed)


def test_provenance_changes_replay_digest() -> None:
    request = _request()
    with_provenance = request.model_copy(
        update={"input_provenance": {"issue:#42": "your branch name"}}
    )
    statuses = [_status("github_pr_metadata", "git_hosting")]

    base = broker_answer(request, [], statuses)
    derived = broker_answer(with_provenance, [], statuses)

    assert base.selection.snapshot_digest != derived.selection.snapshot_digest
