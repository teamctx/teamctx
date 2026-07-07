"""The sound consumer rule: evaluate a query proposition against the broker's answer.

This is where observable soundness (Theorem 2) becomes code, not prose. Given a
``query``, the typed certified claims ``C`` (claim cards), and the per-proposition
coverage closure ``kappa`` (κ), ``evaluate`` under-approximates the three-valued
semantics: it answers True or False only when justified, by a witness or by exhaustive
absence under a *complete* closure, and Unknown otherwise. The absence-branch gates on
completeness: the absence of a refuting card never licenses "clear".

Pure: dataclasses, typing, and internal core imports only (the core purity test guards it).
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Literal

from teamctx.core.contracts import ClosureLike, ClosureStatus, closure_projection
from teamctx.core.kinds import ClaimCard, shape_of, witnesses
from teamctx.core.prop import Prop


@dataclass(frozen=True)
class Valuation:
    """A three-valued verdict for a query. ``reason`` is set only when value is 'unknown'."""

    value: Literal["true", "false", "unknown"]
    reason: str = ""


def _closure_status(query: Prop, closure: tuple[ClosureLike, ...]) -> ClosureStatus:
    for entry in closure:
        projection = closure_projection(entry)
        if projection.proposition == query.predicate:
            return projection.status
    # No closure assessed for this query -> conservatively treat as not complete.
    return "incomplete[policy-gap]"


def evaluate(
    query: Prop,
    claim_cards: tuple[ClaimCard, ...],
    closure: tuple[ClosureLike, ...],
) -> Valuation:
    """Soundly under-approximate the truth of ``query`` from the broker's answer."""

    supports = any(witnesses(card.claim, query) == "supports" for card in claim_cards)
    refutes = any(witnesses(card.claim, query) == "refutes" for card in claim_cards)

    if supports and refutes:
        return Valuation("unknown", "conflicting-evidence")

    status = _closure_status(query, closure)
    if shape_of(query) == "universal":
        if refutes:
            return Valuation("false")  # one counterexample falsifies a universal
        if status == "complete":
            return Valuation("true")  # exhaustive absence under a complete closure
        return Valuation("unknown", status)
    # existential
    if supports:
        return Valuation("true")
    if status == "complete":
        return Valuation("false")
    return Valuation("unknown", status)
