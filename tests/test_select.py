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
from teamctx.core.select import derive_cards

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
