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

from teamctx.core.contracts import CoreContractDocument, SourceSignal, SourceStatus
from teamctx.core.evaluate import Valuation, evaluate
from teamctx.core.prop import Prop, SubjectRef, witnesses
from teamctx.core.select import (
    ClaimCard,
    assess_completeness,
    build_coverage,
    deps_for,
    derive_cards,
    derive_claims,
    no_conflict_query,
    render_collision_claim,
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


def test_closure_policy_gap_when_git_hosting_unobserved() -> None:
    # the fixture has only a docs source — the mandated git_hosting source is absent.
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
    assert len(selection.closure) == 1
    entry = selection.closure[0]
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
