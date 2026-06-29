"""Map the broker's answer to one glanceable hook signal: ready / heads up / can't verify.

The hook injects a short signal before an edit, not the full CLI report. Per the surfaced-text
principle, it speaks to a human about to decide: a clean *ready* that names what it checked, a
*heads up* with the specific item, or *can't verify* when a source that matters was unreachable.
Low-stakes coverage gaps (a check not configured) are never headlined.
"""

from __future__ import annotations

from teamctx.assessment import CheckState, assess
from teamctx.core.broker import BrokerAnswer
from teamctx.core.contracts import ContextCard

_CLEAR_PHRASE = {
    "conflict": "no open pull requests touch these files",
    "gate": "CI is green",
    "docs": "the docs you rely on are current",
    "criteria": "the linked issue's criteria are unchanged",
}


def hook_signal(answer: BrokerAnswer, *, file_path: str, token_present: bool) -> str:
    """One glanceable signal for the PreToolUse injection. Empty string = nothing worth saying."""

    a = assess(answer)
    if a.kind == "heads_up":
        return _heads_up(a.findings, file_path)
    if a.kind == "cant_verify":
        return _cant_verify(token_present)
    return _ready(a.checks, file_path)


def _heads_up(findings: tuple[ContextCard, ...], file_path: str) -> str:
    lines = [f"teamctx: before you edit {file_path}, from the team's current work:"]
    lines.extend(f"  • {card.text} ({card.why_this_matters})" for card in findings)
    lines.append(
        "Factor these into your plan, and surface anything relevant to your human "
        "collaborator so they can decide."
    )
    return "\n".join(lines)


def _cant_verify(token_present: bool) -> str:
    if not token_present:
        return (
            "teamctx couldn't check what else is happening around this file. It doesn't have "
            "access to GitHub yet. To switch that on, set GITHUB_TOKEN in your environment "
            "(or GITHUB_TOKEN_FILE with a path to a token file). If you'd rather not connect "
            "it right now, keep working; you just won't get a heads-up about open pull requests "
            "on the same files or checks that are failing."
        )
    return (
        "teamctx couldn't reach GitHub just now, so it couldn't check for open pull requests or "
        "failing checks on these files. This is likely a transient connection issue. You won't "
        "get those warnings this session, so glance at GitHub yourself if this file is sensitive."
    )


def _ready(checks: tuple[CheckState, ...], file_path: str) -> str:
    clear = [_CLEAR_PHRASE[s.check] for s in checks if s.status == "clear"]
    if not clear:
        return ""
    return f"teamctx: looks clear to start on {file_path} ({_join(clear)})."


def _join(items: list[str]) -> str:
    if len(items) == 1:
        return items[0]
    return ", ".join(items[:-1]) + ", and " + items[-1]
