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

CheckId = Literal["conflict", "criteria", "docs", "gate"]
CheckStatus = Literal["clear", "found", "unreachable", "not_configured"]

# Verdict labels are CARD_KINDS[*].verdict_label in core/select.py. Keep in sync; a mismatch
# makes verdicts.get(label) miss and the check fall to not_configured (caught by the render tests).
_LABELS: tuple[tuple[str, CheckId], ...] = (
    ("Conflict check", "conflict"),
    ("Criteria check", "criteria"),
    ("Docs check", "docs"),
    ("Gate check", "gate"),
)
_REASON_PREFIX: dict[str, CheckId] = {
    "collision": "conflict", "criteria": "criteria", "doc": "docs", "gate": "gate",
}
_IMPORTANT: frozenset[CheckId] = frozenset({"conflict", "gate"})


@dataclass(frozen=True)
class CheckState:
    check: CheckId
    status: CheckStatus
    cards: tuple[ContextCard, ...]


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
    return "not_configured"


def _check_of_card(card: ContextCard) -> CheckId | None:
    return _REASON_PREFIX.get(card.reason_code.split(".", 1)[0])


def assess(answer: BrokerAnswer) -> WorkStartAssessment:
    verdicts: dict[str, Valuation] = {label: val for label, val in answer.verdicts}
    cards_by_check: dict[CheckId, list[ContextCard]] = {
        "conflict": [], "criteria": [], "docs": [], "gate": []
    }
    findings: list[ContextCard] = []
    for card in answer.selection.cards:
        check = _check_of_card(card)
        if check is not None:
            cards_by_check[check].append(card)
            findings.append(card)

    states: list[CheckState] = []
    for label, check in _LABELS:
        valuation = verdicts.get(label)
        status: CheckStatus = _status_for(valuation) if valuation is not None else "not_configured"
        states.append(CheckState(check=check, status=status, cards=tuple(cards_by_check[check])))

    kind: Literal["ready", "heads_up", "cant_verify"]
    if any(s.status == "found" for s in states):
        kind = "heads_up"
    elif any(s.status == "unreachable" and s.check in _IMPORTANT for s in states):
        kind = "cant_verify"
    else:
        kind = "ready"
    return WorkStartAssessment(kind=kind, checks=tuple(states), findings=tuple(findings))
