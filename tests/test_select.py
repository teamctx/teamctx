"""Deterministic card derivation: signals + request -> cards (the broker's heart).

The broker DERIVES context cards from source signals and the request context, rather
than rendering authored cards. The first card kind is the collision: an open-PR signal
whose changed files structurally overlap the paths the requester is about to touch.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any, cast

import pytest

from teamctx.core.authority import AuthorityDecl
from teamctx.core.contracts import (
    CoreContractDocument,
    PolicyDecision,
    RequestContext,
    SourceSignal,
    SourceStatus,
)
from teamctx.core.evaluate import Valuation, evaluate
from teamctx.core.prop import Prop, SubjectRef, witnesses
from teamctx.core.select import (
    CARD_KINDS,
    ClaimCard,
    _derive_doc_superseded_claim,
    all_gates_pass_query,
    assess_completeness,
    build_coverage,
    criteria_changed_query,
    deps_for,
    derive_cards,
    derive_claims,
    no_conflict_query,
    no_superseded_docs_query,
    project_visible_signals,
    render_collision_claim,
    render_doc_superseded_claim,
    select_context,
)

ROOT = Path(__file__).resolve().parent.parent
CONTRACT_FIXTURE = (
    ROOT / "docs/product/discovery/fixtures/contracts/v0/core-contract-document.json"
)


def load_document() -> CoreContractDocument:
    data = cast("dict[str, Any]", json.loads(CONTRACT_FIXTURE.read_text(encoding="utf-8")))
    return CoreContractDocument.model_validate(data)


def collision_signal() -> SourceSignal:
    document = load_document()
    return next(signal for signal in document.source_signals if signal.signal_type == "collision")


def hidden(signal: SourceSignal) -> SourceSignal:
    data = signal.model_dump()
    data["visibility"] = "hidden"
    data["policy"]["can_render_to_agent"] = False
    data["policy"]["can_include_source_text"] = False
    return SourceSignal.model_validate(data)


def test_hidden_collision_signal_derives_no_card() -> None:
    document = load_document()

    cards = derive_cards(document.request_context, [hidden(collision_signal())])

    assert cards == []


def test_collision_signal_overlapping_request_path_derives_a_card() -> None:
    document = load_document()

    cards = derive_cards(document.request_context, [collision_signal()])

    assert len(cards) == 1
    card = cards[0]
    assert card.section == "Needs attention"
    assert card.refs == ["sig_pr_482_collision"]
    assert card.text == "Another open PR changed src/auth/token.py 11 minutes ago."
    assert card.source_display == "GitHub PR #482"
    assert card.freshness == "fresh"
    assert card.confidence == "high"
    assert card.agent_instruction == "verify_before_relying"
    # The credibility engine: the reason names the structural overlap it was derived from.
    assert "src/auth/token.py" in card.reason


def test_collision_signal_with_no_path_overlap_derives_no_card() -> None:
    document = load_document()
    request = document.request_context.model_copy(update={"paths": ["src/other/unrelated.py"]})

    cards = derive_cards(request, [collision_signal()])

    assert cards == []


def test_collision_signal_in_a_different_repo_derives_no_card() -> None:
    document = load_document()
    request = document.request_context.model_copy(update={"repo": "another-service"})

    cards = derive_cards(request, [collision_signal()])

    assert cards == []


def test_only_collision_signals_derive_cards_in_this_vertical() -> None:
    document = load_document()

    cards = derive_cards(document.request_context, document.source_signals)

    assert [card.refs[0] for card in cards] == ["sig_pr_482_collision"]


def test_collision_derives_a_typed_claim_that_witnesses_the_negation() -> None:
    document = load_document()
    request = document.request_context

    claim_cards = derive_claims(request, [collision_signal()])

    assert len(claim_cards) == 1
    claim_card = claim_cards[0]
    assert isinstance(claim_card, ClaimCard)
    assert claim_card.claim.predicate == "pr_conflicts_with_path"
    assert claim_card.claim.shape == "existential"
    assert claim_card.claim.args == ("sig_pr_482_collision",)
    # the card witnesses NOT "no conflict": a counterexample to the universal query.
    assert witnesses(claim_card.claim, no_conflict_query(request)) == "refutes"


def test_hidden_collision_signal_derives_no_claim() -> None:
    document = load_document()

    claim_cards = derive_claims(document.request_context, [hidden(collision_signal())])

    assert claim_cards == []


def test_render_collision_claim_reproduces_the_context_card() -> None:
    document = load_document()
    claim_card = derive_claims(document.request_context, [collision_signal()])[0]

    card = render_collision_claim(claim_card)

    # byte-for-byte the same card the pre-typed derivation produced.
    assert card.section == "Needs attention"
    assert card.refs == ["sig_pr_482_collision"]
    assert card.text == "Another open PR changed src/auth/token.py 11 minutes ago."
    assert card.source_display == "GitHub PR #482"
    assert card.freshness == "fresh"
    assert card.confidence == "high"
    assert card.agent_instruction == "verify_before_relying"
    assert card.source_body == "status_only"
    assert "src/auth/token.py" in card.reason


def _git_hosting_status(status: str) -> SourceStatus:
    """A git_hosting SourceStatus for closure tests (derived from the fixture's status)."""
    base = load_document().source_statuses[0]
    return base.model_copy(
        update={"source_id": "github_pr_metadata", "source_family": "git_hosting", "status": status}
    )


def _collision_query() -> Prop:
    return Prop(
        predicate="no_pr_conflicts_with_paths",
        subject=SubjectRef(repo="auth-service", paths=("src/auth/token.py",)),
    )


def test_deps_for_collision_query_is_git_hosting() -> None:
    assert deps_for(_collision_query()) == frozenset({"git_hosting"})


def test_deps_for_unregistered_predicate_raises() -> None:
    with pytest.raises(ValueError, match="no dependency closure registered"):
        deps_for(Prop(predicate="some_unmodeled_predicate", subject=SubjectRef(repo="r")))


def test_closure_complete_when_git_hosting_fresh() -> None:
    coverage = build_coverage([_git_hosting_status("fresh")])
    assert assess_completeness(_collision_query(), coverage) == "complete"


def test_closure_stale_dep_when_git_hosting_not_fresh() -> None:
    coverage = build_coverage([_git_hosting_status("stale")])
    assert assess_completeness(_collision_query(), coverage) == "incomplete[stale-dep]"


def test_closure_pending_when_dependency_pending() -> None:
    coverage = build_coverage([_git_hosting_status("pending")])
    assert assess_completeness(_collision_query(), coverage) == "incomplete[pending]"


def test_closure_not_applicable_when_dependency_out_of_scope() -> None:
    coverage = build_coverage([_git_hosting_status("not_applicable")])
    assert assess_completeness(_collision_query(), coverage) == "not_applicable[out-of-scope]"


def test_closure_stale_dominates_pending() -> None:
    # a real unreachable dependency beats a pending one within the same family.
    coverage = build_coverage([_git_hosting_status("unavailable"), _git_hosting_status("pending")])
    assert assess_completeness(_collision_query(), coverage) == "incomplete[stale-dep]"


def test_closure_pending_dominates_not_applicable() -> None:
    coverage = build_coverage(
        [_git_hosting_status("pending"), _git_hosting_status("not_applicable")]
    )
    assert assess_completeness(_collision_query(), coverage) == "incomplete[pending]"


def test_closure_policy_gap_when_git_hosting_unobserved() -> None:
    # the fixture has only a docs source; the mandated git_hosting source is absent.
    coverage = build_coverage(load_document().source_statuses)
    assert assess_completeness(_collision_query(), coverage) == "incomplete[policy-gap]"


def test_closure_policy_gap_when_no_sources_checked() -> None:
    assert assess_completeness(_collision_query(), build_coverage([])) == "incomplete[policy-gap]"


def test_select_context_carries_the_collision_query_closure() -> None:
    document = load_document()

    selection = select_context(
        document.request_context, document.source_signals, document.source_statuses
    )

    assert [card.refs[0] for card in selection.cards] == ["sig_pr_482_collision"]
    collision_entries = [
        e for e in selection.closure if e.proposition == "no_pr_conflicts_with_paths"
    ]
    assert len(collision_entries) == 1
    entry = collision_entries[0]
    assert entry.proposition == "no_pr_conflicts_with_paths"
    # the fixture observes no git_hosting source -> the collision query is policy-gapped.
    assert entry.status == "incomplete[policy-gap]"


def test_coverage_reports_each_checked_source_status() -> None:
    # per-source health is still surfaced (absence of cards is never clearance).
    coverage = build_coverage(load_document().source_statuses)
    assert any(entry.status == "stale" for entry in coverage.entries)


def test_collision_closure_is_complete_only_when_git_hosting_is_fresh() -> None:
    fresh = assess_completeness(_collision_query(), build_coverage([_git_hosting_status("fresh")]))
    stale = assess_completeness(_collision_query(), build_coverage([_git_hosting_status("stale")]))
    assert fresh == "complete"
    assert stale == "incomplete[stale-dep]"


def test_select_context_exposes_typed_claim_cards() -> None:
    document = load_document()
    selection = select_context(
        document.request_context, document.source_signals, document.source_statuses
    )
    assert len(selection.claim_cards) == 1
    assert selection.claim_cards[0].claim.predicate == "pr_conflicts_with_path"


def test_evaluate_against_a_real_selection_is_false_when_a_collision_is_present() -> None:
    document = load_document()
    selection = select_context(
        document.request_context, document.source_signals, document.source_statuses
    )
    verdict = evaluate(
        no_conflict_query(document.request_context),
        selection.claim_cards,
        selection.closure,
    )
    assert verdict == Valuation("false")


def test_evaluate_against_a_real_selection_is_unknown_when_clear_but_coverage_gapped() -> None:
    document = load_document()
    request = document.request_context.model_copy(update={"paths": ["src/nothing/here.py"]})
    selection = select_context(request, document.source_signals, document.source_statuses)
    verdict = evaluate(no_conflict_query(request), selection.claim_cards, selection.closure)
    assert selection.claim_cards == ()
    assert verdict == Valuation("unknown", "incomplete[policy-gap]")


def test_evaluate_against_a_real_selection_is_true_when_clear_and_coverage_complete() -> None:
    document = load_document()
    request = document.request_context.model_copy(update={"paths": ["src/nothing/here.py"]})
    selection = select_context(request, document.source_signals, [_git_hosting_status("fresh")])
    verdict = evaluate(no_conflict_query(request), selection.claim_cards, selection.closure)
    assert verdict == Valuation("true")


def test_project_visible_signals_drops_invisible_signals() -> None:
    visible = collision_signal()
    invisible = hidden(collision_signal())
    assert project_visible_signals([visible]) == [visible]
    assert project_visible_signals([invisible]) == []


def test_adding_an_invisible_signal_does_not_change_the_observable() -> None:
    # Theorem 5: the observable is invariant under a P-invisible signal.
    document = load_document()
    request = document.request_context
    statuses = document.source_statuses
    visible = collision_signal()
    invisible = hidden(collision_signal())

    base = select_context(request, [visible], statuses)
    perturbed = select_context(request, [visible, invisible], statuses)

    assert base.cards == perturbed.cards
    assert base.claim_cards == perturbed.claim_cards
    assert base.closure == perturbed.closure
    # The replay digest is part of the observable too: hashing the raw signals would let a
    # consumer detect that an invisible input exists. It must be over the P-visible set.
    assert base.snapshot_digest == perturbed.snapshot_digest
    # The whole answer is invariant, not just the parts we spot-check above.
    assert base == perturbed


def test_selection_has_a_separate_empty_hint_layer() -> None:
    document = load_document()
    selection = select_context(
        document.request_context, document.source_signals, document.source_statuses
    )
    assert selection.hints == ()


def test_coverage_carries_a_delta_dial_defaulting_to_none() -> None:
    assert build_coverage([]).delta == "none"


def test_card_kinds_registry_has_collision() -> None:
    signal_types = {kind.signal_type for kind in CARD_KINDS}
    assert "collision" in signal_types


def test_select_context_still_derives_only_collision_in_this_registry() -> None:
    document = load_document()
    selection = select_context(
        document.request_context, document.source_signals, document.source_statuses
    )
    assert [c.refs[0] for c in selection.cards] == ["sig_pr_482_collision"]
    props = {e.proposition for e in selection.closure}
    assert "no_pr_conflicts_with_paths" in props


def _criteria_signal(issue: str, repo: str = "auth-service") -> SourceSignal:
    return SourceSignal(
        schema_version="teamctx.source_signal.v0",
        id=f"sig_criteria_{issue}",
        signal_type="criteria_changed",
        source_family="issue_tracker",
        scope={"repo": repo, "issue": issue},
        evidence_summary=f"Acceptance criteria for {issue} changed.",
        source_display=f"Issue {issue}",
        freshness="fresh",
        confidence="high",
        visibility="visible",
        created_at="2026-01-01T00:00:00Z",
        observed_at="2026-01-01T00:00:00Z",
        expires_at="next_refresh",
        policy=PolicyDecision(
            schema_version="teamctx.policy_decision.v0",
            can_render_to_user=True,
            can_render_to_agent=True,
            can_include_source_text=False,
            requires_review_for_guidance=False,
            decision_reason="issue metadata is allowed as evidence",
        ),
    )


def test_criteria_changed_derives_a_claim_for_a_linked_issue() -> None:
    document = load_document()
    request = document.request_context.model_copy(update={"linked_issues": ["PROJ-123"]})

    claim_cards = derive_claims(request, [_criteria_signal("PROJ-123")])

    assert len(claim_cards) == 1
    assert claim_cards[0].claim.predicate == "issue_criteria_changed"
    assert witnesses(claim_cards[0].claim, criteria_changed_query(request)) == "refutes"


def test_criteria_changed_ignores_an_unlinked_issue() -> None:
    document = load_document()
    request = document.request_context.model_copy(update={"linked_issues": ["PROJ-999"]})

    assert derive_claims(request, [_criteria_signal("PROJ-123")]) == []


def test_select_context_closure_includes_collision_and_criteria_entries() -> None:
    document = load_document()
    selection = select_context(
        document.request_context, document.source_signals, document.source_statuses
    )
    props = {e.proposition for e in selection.closure}
    assert "no_pr_conflicts_with_paths" in props
    assert "no_criteria_changed_for_issues" in props


def _typed_signal(signal_type: str, source_family: str, scope: dict, sid: str) -> SourceSignal:
    return SourceSignal(
        schema_version="teamctx.source_signal.v0",
        id=sid,
        signal_type=signal_type,
        source_family=source_family,
        scope=scope,
        evidence_summary=f"{signal_type} on {sorted(scope.values(), key=str)}",
        source_display=sid,
        freshness="fresh",
        confidence="high",
        visibility="visible",
        created_at="2026-01-01T00:00:00Z",
        observed_at="2026-01-01T00:00:00Z",
        expires_at="next_refresh",
        policy=PolicyDecision(
            schema_version="teamctx.policy_decision.v0",
            can_render_to_user=True,
            can_render_to_agent=True,
            can_include_source_text=False,
            requires_review_for_guidance=False,
            decision_reason="metadata allowed as evidence",
        ),
    )


def test_doc_superseded_derives_for_a_relied_on_doc() -> None:
    document = load_document()
    request = document.request_context  # repo auth-service, paths [src/auth/token.py]
    signal = _typed_signal(
        "doc_superseded", "docs", {"repo": "auth-service", "doc": "src/auth/token.py"}, "sig_doc_1"
    )
    claim_cards = derive_claims(request, [signal])
    assert len(claim_cards) == 1
    assert claim_cards[0].claim.predicate == "doc_superseded"
    assert witnesses(claim_cards[0].claim, no_superseded_docs_query(request)) == "refutes"


def test_doc_superseded_ignores_an_unrelated_doc() -> None:
    document = load_document()
    signal = _typed_signal(
        "doc_superseded", "docs", {"repo": "auth-service", "doc": "src/other/x.py"}, "sig_doc_2"
    )
    assert derive_claims(document.request_context, [signal]) == []


def test_missed_gate_derives_for_a_failing_gate_on_a_touched_file() -> None:
    document = load_document()
    request = document.request_context
    signal = _typed_signal(
        "missed_gate", "ci_deploy",
        {"repo": "auth-service", "files": ["src/auth/token.py"]}, "sig_gate_1",
    )
    claim_cards = derive_claims(request, [signal])
    assert len(claim_cards) == 1
    assert claim_cards[0].claim.predicate == "gate_failed"
    assert witnesses(claim_cards[0].claim, all_gates_pass_query(request)) == "refutes"


def test_missed_gate_ignores_a_gate_on_other_files() -> None:
    document = load_document()
    signal = _typed_signal(
        "missed_gate",
        "ci_deploy",
        {"repo": "auth-service", "files": ["src/other/x.py"]},
        "sig_gate_2",
    )
    assert derive_claims(document.request_context, [signal]) == []


def test_select_context_has_four_closure_entries() -> None:
    document = load_document()
    selection = select_context(
        document.request_context, document.source_signals, document.source_statuses
    )
    assert {e.proposition for e in selection.closure} == {
        "no_pr_conflicts_with_paths",
        "no_criteria_changed_for_issues",
        "no_superseded_docs",
        "all_gates_pass",
    }


def test_select_context_carries_authority_for_declared_subjects() -> None:
    document = load_document()
    declarations = [
        AuthorityDecl(subject="rounding-cap", source="policy", priority=10, value="3", fresh=True),
    ]
    selection = select_context(
        document.request_context,
        document.source_signals,
        document.source_statuses,
        declarations,
    )
    assert len(selection.authority) == 1
    assert selection.authority[0].subject == "rounding-cap"
    assert selection.authority[0].state == "resolved"


def test_select_context_with_no_declarations_has_empty_authority() -> None:
    document = load_document()
    selection = select_context(
        document.request_context, document.source_signals, document.source_statuses
    )
    assert selection.authority == ()


def test_select_context_is_replayable_with_a_stable_digest() -> None:
    document = load_document()
    a = select_context(
        document.request_context, document.source_signals, document.source_statuses
    )
    b = select_context(
        document.request_context, document.source_signals, document.source_statuses
    )
    # determinism: identical inputs -> identical answer, bound by an identical digest.
    assert a == b
    assert a.snapshot_digest == b.snapshot_digest
    assert len(a.snapshot_digest) == 64


def test_collision_card_has_reason_code_and_severity() -> None:
    document = load_document()
    selection = select_context(
        document.request_context, document.source_signals, document.source_statuses
    )
    card = selection.cards[0]
    assert card.reason_code == "collision.same_path"
    assert card.severity is not None
    assert card.severity.kind_base == 0.8


def _request_context(repo: str, paths: list[str]) -> RequestContext:
    return RequestContext(
        schema_version="teamctx.request_context.v0",
        request_id="req_test",
        repo=repo,
        task="test task",
        paths=paths,
        requested_at="2026-01-01T00:00:00Z",
    )


def test_doc_superseded_card_names_the_superseding_doc() -> None:
    request = _request_context("r", ["docs/old.md"])
    signal = _typed_signal(
        "doc_superseded",
        "docs",
        {"repo": "r", "doc": "docs/old.md", "superseded_by": "docs/new.md"},
        "sig_doc_x",
    )
    claim_card = _derive_doc_superseded_claim(request, signal)
    assert claim_card is not None
    card = render_doc_superseded_claim(claim_card)
    assert "docs/new.md" in card.why_this_matters
    assert "docs/new.md" in card.reason


def test_doc_superseded_card_falls_back_without_superseding_doc() -> None:
    request = _request_context("r", ["docs/old.md"])
    signal = _typed_signal(
        "doc_superseded", "docs", {"repo": "r", "doc": "docs/old.md"}, "sig_doc_y"
    )
    claim_card = _derive_doc_superseded_claim(request, signal)
    assert claim_card is not None
    card = render_doc_superseded_claim(claim_card)
    assert card.why_this_matters == (
        "the doc docs/old.md was superseded; verify it is current before relying."
    )
