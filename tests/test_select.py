"""Deterministic card derivation: signals + request -> cards (the broker's heart).

The broker DERIVES context cards from source signals and the request context, rather
than rendering authored cards. The first card kind is the collision: an open-PR signal
whose changed files structurally overlap the paths the requester is about to touch.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any, cast

from teamctx.core.contracts import CoreContractDocument, SourceSignal
from teamctx.core.prop import witnesses
from teamctx.core.select import (
    ClaimCard,
    build_coverage,
    derive_cards,
    derive_claims,
    no_conflict_query,
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


def test_a_stale_source_makes_coverage_incomplete_and_is_reported() -> None:
    document = load_document()

    coverage = build_coverage(document.source_statuses)

    # absence is never clearance: a stale source means we cannot call coverage complete.
    assert coverage.complete is False
    assert any(entry.status == "stale" for entry in coverage.entries)


def test_no_checked_sources_is_not_complete_coverage() -> None:
    # Zero observation is the strongest "Unknown", not "all clear".
    coverage = build_coverage([])

    assert coverage.complete is False


def test_all_fresh_sources_make_coverage_complete() -> None:
    document = load_document()
    fresh = document.source_statuses[0].model_copy(update={"status": "fresh"})

    coverage = build_coverage([fresh])

    assert coverage.complete is True
    assert coverage.entries[0].status == "fresh"


def test_select_context_returns_derived_cards_and_coverage_together() -> None:
    document = load_document()

    selection = select_context(
        document.request_context, document.source_signals, document.source_statuses
    )

    # cards are DERIVED (not the authored fixture cards), and coverage is reported
    assert [card.refs[0] for card in selection.cards] == ["sig_pr_482_collision"]
    assert selection.coverage.complete is False  # the fixture carries a stale source


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
