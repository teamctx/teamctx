"""Deterministic card selection for the fixture-backed prototype."""

from __future__ import annotations

from collections.abc import Iterable

from teamctx.core.models import ContextCard, Fixture, GuidanceRecord, SourceSignal

AGENT_PROMPT_SIGNAL_TYPES = frozenset({"collision", "changed_since_start"})
SOURCE_HEALTH_FRESHNESS = frozenset({"blocked", "stale", "unavailable"})

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


def select_agent_prompt_cards(
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

        if card_allowed_in_agent_prompt(fixture, card):
            cards.append(card)

    return sort_cards(cards)


def select_source_status_cards(
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

        if card_allowed_in_source_status(fixture, card):
            cards.append(card)

    return sort_cards(cards)


def card_allowed_in_agent_prompt(fixture: Fixture, card: ContextCard) -> bool:
    if not card.default_agent_visible or card.relevance is not None:
        return False

    if not card.refs:
        return False

    for ref in card.refs:
        signal = find_signal(fixture, ref)
        if signal is not None:
            if not source_signal_allowed_in_agent_prompt(signal):
                return False
            continue

        guidance = find_guidance(fixture, ref)
        if guidance is not None:
            if not guidance_allowed_in_agent_prompt(guidance):
                return False
            continue

        return False

    return True


def card_allowed_in_source_status(fixture: Fixture, card: ContextCard) -> bool:
    if not card.default_agent_visible or card.relevance is not None:
        return False

    if not card.refs:
        return False

    has_source_status = False
    for ref in card.refs:
        signal = find_signal(fixture, ref)
        if signal is None:
            return False
        if source_signal_allowed_in_source_status(signal):
            has_source_status = True

    return has_source_status


def source_signal_allowed_in_agent_prompt(signal: SourceSignal) -> bool:
    if not signal.policy.can_render_to_agent:
        return False
    if signal.visibility == "warning_only":
        return False
    if signal.freshness in SOURCE_HEALTH_FRESHNESS:
        return False
    if signal.freshness != "fresh":
        return False
    return signal.signal_type in AGENT_PROMPT_SIGNAL_TYPES


def source_signal_allowed_in_source_status(signal: SourceSignal) -> bool:
    if not signal.policy.can_render_to_agent:
        return False
    return signal.visibility == "warning_only" or signal.freshness in SOURCE_HEALTH_FRESHNESS


def guidance_allowed_in_agent_prompt(guidance: GuidanceRecord) -> bool:
    return guidance.status == "active" and guidance.freshness == "fresh"


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
