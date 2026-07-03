"""Map the broker's answer to one glanceable hook signal: ready / heads up / can't verify.

The hook injects a short signal before an edit, not the full CLI report. Per the surfaced-text
principle, it speaks to a human about to decide: a clean *ready* that names what it checked, a
*heads up* with the specific item, or *can't verify* when a source that matters was unreachable.
Low-stakes coverage gaps (a check not configured) are never headlined.
"""

from __future__ import annotations

from teamctx.assessment import IMPORTANT_CHECKS, CheckState, WorkStartAssessment, assess
from teamctx.contract_render import RENDER_COPY
from teamctx.core.broker import BrokerAnswer


def hook_signal(answer: BrokerAnswer, *, file_path: str, token_present: bool) -> str:
    """One glanceable signal for the PreToolUse injection. Empty string = nothing worth saying."""

    a = assess(answer)
    if a.kind == "heads_up":
        return _heads_up(a, file_path)
    if a.kind == "cant_verify":
        return _cant_verify(a, token_present)
    return _ready(a.checks, file_path)


def _important_gap_notes(a: WorkStartAssessment) -> list[str]:
    # Brief, honest notes for important checks that are unconfirmed (unreachable or pending), so a
    # finding-driven heads_up never hides that the gate or PR check could not be confirmed.
    notes: list[str] = []
    for s in a.checks:
        if s.check not in IMPORTANT_CHECKS:
            continue
        if s.status == "pending":
            notes.append("CI checks are still running, so the gate isn't confirmed green yet.")
        elif s.status == "unreachable":
            notes.append(
                "teamctx couldn't reach GitHub to check "
                f"{RENDER_COPY[s.check].hook_gap or s.check}, so it's unconfirmed."
            )
    return notes


def _heads_up(a: WorkStartAssessment, file_path: str) -> str:
    lines = [f"teamctx: before you edit {file_path}, from the team's current work:"]
    lines.extend(f"  • {card.text} ({card.why_this_matters})" for card in a.findings)
    lines.extend(f"  • {note}" for note in _important_gap_notes(a))
    lines.append(
        "Factor these into your plan, and surface anything relevant to your human "
        "collaborator so they can decide."
    )
    return "\n".join(lines)


def _cant_verify(a: WorkStartAssessment, token_present: bool) -> str:
    unreachable = [
        s.check for s in a.checks if s.status == "unreachable" and s.check in IMPORTANT_CHECKS
    ]
    pending = [s.check for s in a.checks if s.status == "pending" and s.check in IMPORTANT_CHECKS]
    parts: list[str] = []
    if unreachable:
        # name only the checks that are actually unreachable, so a pending gate is never
        # mislabeled as "couldn't check failing checks".
        gaps = " or ".join(RENDER_COPY[check].hook_gap or check for check in unreachable)
        if not token_present:
            parts.append(
                f"teamctx couldn't check {gaps} around this file. It doesn't have access to "
                "GitHub yet. To switch that on, set GITHUB_TOKEN in your environment (or "
                "GITHUB_TOKEN_FILE with a path to a token file). If you'd rather not connect it "
                f"right now, keep working; you just won't get a heads-up about {gaps}."
            )
        else:
            parts.append(
                f"teamctx couldn't reach GitHub just now, so it couldn't check {gaps} on these "
                "files. This is likely a transient connection issue. You won't get those warnings "
                "this session, so glance at GitHub yourself if this file is sensitive."
            )
    if pending:
        parts.append(
            "teamctx: CI checks on this branch are still running, so it can't confirm the "
            "gate is green yet. If a green build matters for this edit, wait for it or check "
            "the run yourself."
        )
    return " ".join(parts)


def _ready(checks: tuple[CheckState, ...], file_path: str) -> str:
    clear = [RENDER_COPY[s.check].hook_clear for s in checks if s.status == "clear"]
    if not clear:
        return ""
    return f"teamctx: looks clear to start on {file_path} ({_join(clear)})."


def _join(items: list[str]) -> str:
    if len(items) == 1:
        return items[0]
    return ", ".join(items[:-1]) + ", and " + items[-1]
