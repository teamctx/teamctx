"""Classify the broker's answer into one work-start assessment: kind + per-check status.

One shared classification consumed by both the hook (a glanceable line) and the CLI/MCP render
(a fuller report), so there is a single voice and the important-vs-low-stakes split lives in one
place. Pure: no I/O.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Literal

from teamctx.ambient import Delta, deltas_from_signals, finding_key
from teamctx.core.broker import BrokerAnswer
from teamctx.core.contracts import ContextCard
from teamctx.core.declared import DECLARED_CHECK_SCOPE_KEY, DeclaredCheckCopy
from teamctx.core.evaluate import Valuation
from teamctx.core.kinds import (
    CARD_KINDS,
    CHECK_DEPS_FAMILY,
    LABEL_CHECK_PAIRS,
    REASON_PREFIX,
    CheckId,
)
from teamctx.core.kinds import (
    IMPORTANT_CHECKS as DECLARED_IMPORTANT_CHECKS,
)

CheckStatus = Literal[
    "clear",
    "found",
    "unreachable",
    "not_configured",
    "pending",
    "not_applicable",
    "unbounded",
]

# The verdict-label/check pairs, reason-prefix routing, and important-set are DERIVED from
# core/kinds.py, so a check can never drift out of sync with the declaration that produces it.
IMPORTANT_CHECKS: frozenset[CheckId] = DECLARED_IMPORTANT_CHECKS


@dataclass(frozen=True)
class CheckState:
    check: CheckId
    status: CheckStatus
    cards: tuple[ContextCard, ...]
    note: str | None = None
    failing_sources: tuple[tuple[str, str], ...] = ()  # when unreachable: (source_id, status)
    declared_copy: DeclaredCheckCopy | None = None


@dataclass(frozen=True)
class WorkStartAssessment:
    kind: Literal["ready", "heads_up", "cant_verify"]
    checks: tuple[CheckState, ...]
    findings: tuple[ContextCard, ...]
    important_checks: frozenset[CheckId] = frozenset()
    # What changed since the session baseline. The kind above is the CURRENT world and never moves
    # because of a delta; deltas are a separate lane the render speaks first.
    deltas: tuple[Delta, ...] = ()


AnswerClass = Literal["GOOD", "GAP-KNOWN", "NONE"]


def class_of_answer(assessment: WorkStartAssessment) -> AnswerClass:
    """Classify whether an ambient baseline can legally serve silence for important checks."""

    important = [
        state for state in assessment.checks if state.check in assessment.important_checks
    ]
    if important and all(state.status in {"clear", "found"} for state in important):
        return "GOOD"
    if important:
        # Any surfaced non-positive state (unreachable, pending, unbounded, not_configured,
        # not_applicable) is a KNOWN, stated condition: the answer said so out loud. It is a
        # legal baseline for interval silence under the gap rules; falling through to NONE
        # here would make decide() treat every edit as first-contact and re-speak forever
        # (found live: a repo with no branch has a not_configured gate on every answer).
        return "GAP-KNOWN"
    return "NONE"


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
    declared = card.scope.get(DECLARED_CHECK_SCOPE_KEY)
    if isinstance(declared, str) and declared:
        return declared
    return REASON_PREFIX.get(card.reason_code.split(".", 1)[0])


def card_finding_key(card: ContextCard) -> str | None:
    """The delta identity key of a finding card, so the render can suppress the steady bullet for a
    finding a fresh-appearance delta already spoke (one fact, one voice)."""

    check = _check_of_card(card)
    if check is None:
        return None
    return finding_key(check, card.scope)


def assess(answer: BrokerAnswer) -> WorkStartAssessment:
    verdicts: dict[str, Valuation] = {label: val for label, val in answer.verdicts}
    if answer.enabled_checks or answer.disabled_checks or answer.important_checks:
        enabled_checks = answer.enabled_checks
        important_checks = frozenset(answer.important_checks)
    else:
        enabled_checks = tuple(kind.check_id for kind in CARD_KINDS)
        important_checks = IMPORTANT_CHECKS
    enabled = set(enabled_checks)
    cards_by_check: dict[CheckId, list[ContextCard]] = {
        kind.check_id: [] for kind in CARD_KINDS if kind.check_id in enabled
    }
    coverage_notes = _coverage_notes_by_family_and_status(answer)
    failing_by_family = _failing_source_ids_by_family(answer)
    findings: list[ContextCard] = []
    for card in answer.selection.cards:
        check = _check_of_card(card)
        if check is not None and check in enabled:
            cards_by_check.setdefault(check, []).append(card)
            findings.append(card)

    states: list[CheckState] = []
    for label, check in LABEL_CHECK_PAIRS:
        if check not in enabled:
            continue
        valuation = verdicts.get(label)
        status: CheckStatus = _status_for(valuation) if valuation is not None else "not_configured"
        states.append(
            CheckState(
                check=check,
                status=status,
                cards=tuple(cards_by_check[check]),
                note=_note_for(check, status, coverage_notes),
                failing_sources=(
                    failing_by_family.get(CHECK_DEPS_FAMILY[check], ())
                    if status == "unreachable"
                    else ()
                ),
            )
        )
    for evaluation in answer.selection.declared_evaluations:
        states.append(
            CheckState(
                check=evaluation.check_id,
                status=evaluation.status,
                cards=evaluation.cards,
                note=evaluation.note,
                failing_sources=evaluation.failing_sources,
                declared_copy=next(
                    (
                        check.copy
                        for check in answer.declared_checks
                        if check.id == evaluation.check_id
                    ),
                    None,
                ),
            )
        )

    kind: Literal["ready", "heads_up", "cant_verify"]
    if any(s.status == "found" for s in states):
        kind = "heads_up"
    elif any(
        s.status in {"unreachable", "pending", "unbounded"} and s.check in important_checks
        for s in states
    ):
        kind = "cant_verify"
    else:
        kind = "ready"
    return WorkStartAssessment(
        kind=kind,
        checks=tuple(states),
        findings=tuple(findings),
        important_checks=important_checks,
        deltas=deltas_from_signals(answer.source_signals),
    )


def _coverage_notes_by_family_and_status(
    answer: BrokerAnswer,
) -> dict[tuple[str, str], tuple[str, ...]]:
    notes: dict[tuple[str, str], list[str]] = {}
    for entry in answer.selection.coverage.entries:
        if entry.status in {"disabled", "unbounded", "stale", "not_applicable"} and entry.note:
            notes.setdefault((entry.source_family, entry.status), []).append(entry.note)
    return {key: tuple(values) for key, values in notes.items()}


def _failing_source_ids_by_family(
    answer: BrokerAnswer,
) -> dict[str, tuple[tuple[str, str], ...]]:
    """(source_id, status) pairs whose unhealthy status made a family unreachable, so the render
    can name WHICH source failed and HOW (a Confluence budget hit is "couldn't fully check",
    never "couldn't reach"; a local-folder failure never wears Confluence copy)."""

    failing: dict[str, list[tuple[str, str]]] = {}
    for entry in answer.selection.coverage.entries:
        if entry.status in {"stale", "unavailable", "blocked"}:
            failing.setdefault(entry.source_family, []).append((entry.source_id, entry.status))
    return {family: tuple(pairs) for family, pairs in failing.items()}


def _note_for(
    check: CheckId, status: CheckStatus, coverage_notes: dict[tuple[str, str], tuple[str, ...]]
) -> str | None:
    if status == "unreachable":
        # An unreachable check whose failing sources were all REACHED (stale: a skipped
        # pipeline, an unexhausted budget) carries the connector's precise message so the
        # render never claims a connection problem that did not happen.
        family = CHECK_DEPS_FAMILY[check]
        notes = coverage_notes.get((family, "stale"), ())
        return "; ".join(notes) if notes else None
    if status not in {"not_configured", "unbounded", "not_applicable"}:
        return None
    family = CHECK_DEPS_FAMILY[check]
    coverage_status = "disabled" if status == "not_configured" else status
    notes = coverage_notes.get((family, coverage_status), ())
    return "; ".join(notes) if notes else None
