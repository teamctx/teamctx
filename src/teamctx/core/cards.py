"""Deterministic card selection for the fixture-backed prototype."""

from __future__ import annotations

from collections.abc import Iterable

from teamctx.core.models import ContextCard, Fixture, GuidanceRecord, SourceSignal

SECTION_ORDER = (
    "Needs attention",
    "Project guidance",
    "Verify before relying",
    "Source unavailable",
    "Good to know",
)


def select_cards(
    fixture: Fixture,
    *,
    selected_card_ids: Iterable[str] = (),
    relevance_tags: Iterable[str] = (),
    include_default: bool = True,
) -> list[ContextCard]:
    selected = set(selected_card_ids)
    relevance = set(relevance_tags)
    cards: list[ContextCard] = []

    for card in fixture.expected_cards:
        if card.id in selected:
            cards.append(card)
            continue

        if card.relevance is not None and card.relevance in relevance:
            cards.append(card)
            continue

        if not include_default:
            continue

        if card.default_agent_visible and card.relevance is None:
            cards.append(card)

    return sort_cards(cards)


def sort_cards(cards: Iterable[ContextCard]) -> list[ContextCard]:
    section_rank = {section: index for index, section in enumerate(SECTION_ORDER)}
    return sorted(cards, key=lambda card: section_rank.get(card.section, len(section_rank)))


def find_card(fixture: Fixture, card_id: str) -> ContextCard:
    for card in fixture.expected_cards:
        if card.id == card_id:
            return card
    raise KeyError(card_id)


def find_signal(fixture: Fixture, ref: str) -> SourceSignal | None:
    for signal in fixture.source_signals:
        if signal.id == ref:
            return signal
    return None


def find_guidance(fixture: Fixture, ref: str) -> GuidanceRecord | None:
    for record in fixture.guidance_records:
        if record.id == ref:
            return record
    return None
