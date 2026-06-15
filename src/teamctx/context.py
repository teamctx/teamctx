"""High-level fixture-backed context helpers."""

from __future__ import annotations

from collections.abc import Iterable

from teamctx.core.cards import select_agent_prompt_cards, select_cards
from teamctx.core.models import ContextCard, Fixture
from teamctx.render import render_context_cards


def context_cards(
    fixture: Fixture,
    *,
    selected_card_ids: Iterable[str] = (),
    relevance_tags: Iterable[str] = (),
    include_default: bool = True,
) -> list[ContextCard]:
    return select_cards(
        fixture,
        selected_card_ids=selected_card_ids,
        relevance_tags=relevance_tags,
        include_default=include_default,
    )


def agent_prompt_cards(
    fixture: Fixture,
    *,
    selected_card_ids: Iterable[str] = (),
    relevance_tags: Iterable[str] = (),
    include_default: bool = True,
) -> list[ContextCard]:
    return select_agent_prompt_cards(
        fixture,
        selected_card_ids=selected_card_ids,
        relevance_tags=relevance_tags,
        include_default=include_default,
    )


def render_context(
    fixture: Fixture,
    *,
    selected_card_ids: Iterable[str] = (),
    relevance_tags: Iterable[str] = (),
    include_default: bool = True,
) -> str:
    cards = context_cards(
        fixture,
        selected_card_ids=selected_card_ids,
        relevance_tags=relevance_tags,
        include_default=include_default,
    )
    return render_context_cards(cards)
