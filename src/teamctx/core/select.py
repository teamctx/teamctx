"""Deterministic card derivation from source signals + the request context.

This is the broker's heart: it DERIVES context cards from typed source signals by
computing structural relevance against the request, rather than rendering authored cards.
Pure and deterministic — no I/O, time, or randomness (enforced by the core purity test) —
so every derived card is replayable and its reason names the overlap it came from.
"""

from __future__ import annotations

from collections.abc import Iterable

from teamctx.core.contracts import ContextCard, RequestContext, SourceSignal


def derive_cards(request: RequestContext, signals: Iterable[SourceSignal]) -> list[ContextCard]:
    """Derive context cards from signals by computing structural relevance to the request."""

    cards: list[ContextCard] = []
    for signal in signals:
        if not _is_surfaceable(signal):
            continue
        if signal.signal_type == "collision":
            card = _derive_collision_card(request, signal)
            if card is not None:
                cards.append(card)
    return cards


def _is_surfaceable(signal: SourceSignal) -> bool:
    """Fail-closed: never surface a signal the requester is not permitted to see at all."""

    if signal.visibility in {"hidden", "never"}:
        return False
    return signal.policy.can_render_to_user


def _derive_collision_card(request: RequestContext, signal: SourceSignal) -> ContextCard | None:
    if signal.scope.get("repo") != request.repo:
        return None
    candidate_files = signal.scope.get("files")
    candidate = candidate_files if isinstance(candidate_files, list) else []
    shared = sorted(set(request.paths) & set(candidate))
    if not shared:
        return None
    overlap = ", ".join(shared)
    return ContextCard(
        schema_version="teamctx.context_card.v0",
        id=f"card_{signal.id}",
        section="Needs attention",
        text=signal.evidence_summary,
        why_this_matters=f"you are editing {shared[0]}.",
        source_display=signal.source_display,
        refs=[signal.id],
        reason=f"same repository and file path as the current task: {overlap}",
        scope=signal.scope,
        freshness=signal.freshness,
        confidence=signal.confidence,
        source_body="status_only",
        source_open_target_id=None,
        agent_instruction="verify_before_relying",
    )
