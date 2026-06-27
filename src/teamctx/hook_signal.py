"""Map the broker's answer to one glanceable hook signal: ready / heads up / can't verify.

The hook injects a short signal before an edit — not the full CLI report. Per the surfaced-text
principle, it speaks to a human about to decide: a clean *ready* that names what it checked, a
*heads up* with the specific item, or *can't verify* when a source that matters was unreachable.
Low-stakes coverage gaps (a check not configured) are never headlined.
"""

from __future__ import annotations

from teamctx.core.broker import BrokerAnswer
from teamctx.core.contracts import ContextCard
from teamctx.core.evaluate import Valuation

_IMPORTANT = ("Conflict check", "Gate check")
_CLEAR_PHRASE = {
    "Conflict check": "no open pull requests touch these files",
    "Gate check": "CI is green",
    "Docs check": "the docs you rely on are current",
    "Criteria check": "the linked issue's criteria are unchanged",
}


def hook_signal(answer: BrokerAnswer, *, file_path: str, token_present: bool) -> str:
    """One glanceable signal for the PreToolUse injection. Empty string = nothing worth saying."""

    verdicts: dict[str, Valuation] = {label: val for label, val in answer.verdicts}
    findings = [
        card
        for card in answer.selection.cards
        if card.section in ("Needs attention", "Verify before relying")
    ]
    if findings:
        return _heads_up(findings, file_path)

    blocked = [
        label
        for label in _IMPORTANT
        if label in verdicts
        and verdicts[label].value == "unknown"
        and verdicts[label].reason.startswith("incomplete[stale-dep]")
    ]
    if blocked:
        return _cant_verify(token_present)

    return _ready(verdicts, file_path)


def _heads_up(findings: list[ContextCard], file_path: str) -> str:
    lines = [f"teamctx — before you edit {file_path}, from the team's current work:"]
    lines.extend(f"  • {card.text} — {card.why_this_matters}" for card in findings)
    lines.append("Pass along anything relevant to whoever you're working with so they can decide.")
    return "\n".join(lines)


def _cant_verify(token_present: bool) -> str:
    if not token_present:
        return (
            "teamctx couldn't check what else is happening around this file — it doesn't have "
            "access to GitHub yet. To switch that on, run `teamctx install-hook` and it'll "
            "walk you through giving it a token. If you'd rather not connect it right now, "
            "that's fine — keep working; you just won't get a heads-up about open pull requests "
            "on the same files or checks that are failing."
        )
    return (
        "teamctx couldn't reach GitHub just now, so it couldn't check for open pull requests or "
        "failing checks on these files — usually a passing connection issue, worth a retry. "
        "Until it's back you won't get those warnings, so glance at GitHub yourself if "
        "this file is sensitive."
    )


def _ready(verdicts: dict[str, Valuation], file_path: str) -> str:
    clear = [
        _CLEAR_PHRASE[label]
        for label in ("Conflict check", "Gate check", "Docs check", "Criteria check")
        if label in verdicts and verdicts[label].value == "true"
    ]
    if not clear:
        return ""
    return f"teamctx — looks clear to start on {file_path}: {_join(clear)}."


def _join(items: list[str]) -> str:
    if len(items) == 1:
        return items[0]
    return ", ".join(items[:-1]) + ", and " + items[-1]
