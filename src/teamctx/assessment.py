"""Classify the broker's answer into one work-start assessment: kind + per-check status.

One shared classification consumed by both the hook (a glanceable line) and the CLI/MCP render
(a fuller report), so there is a single voice and the important-vs-low-stakes split lives in one
place. Pure: no I/O.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Literal

from teamctx.core.broker import BrokerAnswer
from teamctx.core.contracts import ContextCard
from teamctx.core.evaluate import Valuation
from teamctx.core.kinds import CHECK_DEPS_FAMILY, LABEL_CHECK_PAIRS, REASON_PREFIX, CheckId

CheckStatus = Literal[
    "clear",
    "found",
    "unreachable",
    "not_configured",
    "pending",
    "not_applicable",
    "unbounded",
]

# The verdict-label-to-check pairs and reason-prefix routing are DERIVED from CARD_KINDS in
# core/kinds.py, so a check can never drift out of sync with the kind that produces it.
IMPORTANT_CHECKS: frozenset[CheckId] = frozenset({"conflict", "gate"})


@dataclass(frozen=True)
class CheckState:
    check: CheckId
    status: CheckStatus
    cards: tuple[ContextCard, ...]
    note: str | None = None
    failing_source_ids: tuple[str, ...] = ()  # set when unreachable: WHICH source failed


@dataclass(frozen=True)
class WorkStartAssessment:
    kind: Literal["ready", "heads_up", "cant_verify"]
    checks: tuple[CheckState, ...]
    findings: tuple[ContextCard, ...]


def _status_for(valuation: Valuation) -> CheckStatus:
    if valuation.value == "true":
        return "clear"
    if valuation.value == "false":
        return "found"
    if valuation.reason == "conflicting-evidence":
        return "found"  # connectors fired and disagree: a finding, not a config gap
    if valuation.reason == "incomplete[stale-dep]":
        return "unreachable"
    if valuation.reason == "incomplete[unbounded]":
        return "unbounded"
    if valuation.reason == "incomplete[pending]":
        return "pending"
    if valuation.reason == "not_applicable[out-of-scope]":
        return "not_applicable"
    return "not_configured"


def _check_of_card(card: ContextCard) -> CheckId | None:
    return REASON_PREFIX.get(card.reason_code.split(".", 1)[0])


def assess(answer: BrokerAnswer) -> WorkStartAssessment:
    verdicts: dict[str, Valuation] = {label: val for label, val in answer.verdicts}
    cards_by_check: dict[CheckId, list[ContextCard]] = {
        "conflict": [], "criteria": [], "docs": [], "gate": []
    }
    coverage_notes = _coverage_notes_by_family_and_status(answer)
    failing_by_family = _failing_source_ids_by_family(answer)
    findings: list[ContextCard] = []
    for card in answer.selection.cards:
        check = _check_of_card(card)
        if check is not None:
            cards_by_check[check].append(card)
            findings.append(card)

    states: list[CheckState] = []
    for label, check in LABEL_CHECK_PAIRS:
        valuation = verdicts.get(label)
        status: CheckStatus = _status_for(valuation) if valuation is not None else "not_configured"
        states.append(
            CheckState(
                check=check,
                status=status,
                cards=tuple(cards_by_check[check]),
                note=_note_for(check, status, coverage_notes),
                failing_source_ids=(
                    failing_by_family.get(CHECK_DEPS_FAMILY[check], ())
                    if status == "unreachable"
                    else ()
                ),
            )
        )

    kind: Literal["ready", "heads_up", "cant_verify"]
    if any(s.status == "found" for s in states):
        kind = "heads_up"
    elif any(
        s.status in {"unreachable", "pending", "unbounded"} and s.check in IMPORTANT_CHECKS
        for s in states
    ):
        kind = "cant_verify"
    else:
        kind = "ready"
    return WorkStartAssessment(kind=kind, checks=tuple(states), findings=tuple(findings))


def _coverage_notes_by_family_and_status(
    answer: BrokerAnswer,
) -> dict[tuple[str, str], tuple[str, ...]]:
    notes: dict[tuple[str, str], list[str]] = {}
    for entry in answer.selection.coverage.entries:
        if entry.status in {"disabled", "unbounded"} and entry.note:
            notes.setdefault((entry.source_family, entry.status), []).append(entry.note)
    return {key: tuple(values) for key, values in notes.items()}


def _failing_source_ids_by_family(answer: BrokerAnswer) -> dict[str, tuple[str, ...]]:
    """The source ids whose unhealthy status made a family unreachable, so the render can name
    WHICH source failed (a Confluence outage must never read "couldn't read the docs folder")."""

    failing: dict[str, list[str]] = {}
    for entry in answer.selection.coverage.entries:
        if entry.status in {"stale", "unavailable", "blocked"}:
            failing.setdefault(entry.source_family, []).append(entry.source_id)
    return {family: tuple(ids) for family, ids in failing.items()}


def _note_for(
    check: CheckId, status: CheckStatus, coverage_notes: dict[tuple[str, str], tuple[str, ...]]
) -> str | None:
    if status not in {"not_configured", "unbounded"}:
        return None
    family = CHECK_DEPS_FAMILY[check]
    coverage_status = "disabled" if status == "not_configured" else "unbounded"
    notes = coverage_notes.get((family, coverage_status), ())
    return "; ".join(notes) if notes else None
