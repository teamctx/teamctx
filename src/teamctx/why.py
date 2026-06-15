"""`Show why` rendering for context cards."""

from __future__ import annotations

from teamctx.core.cards import find_card, find_signal
from teamctx.core.models import Fixture, SourceSignal


def render_why(fixture: Fixture, card_id: str) -> str:
    card = find_card(fixture, card_id)
    signal = next((find_signal(fixture, ref) for ref in card.refs), None)
    if signal is None:
        return _render_generic_why(card.source)

    reason = _reason_line(signal)
    return (
        "Show why\n\n"
        f"{reason}\n\n"
        f"Source: {_source_label(signal)}\n"
        f"Freshness: {signal.freshness}\n"
        f"Scope: {_scope_label(fixture, signal)}\n"
        f"Agent visibility: {_agent_visibility(signal)}\n"
    )


def _reason_line(signal: SourceSignal) -> str:
    files = _files(signal)
    if signal.signal_type == "collision" and files:
        source = signal.source_display
        return (
            f"This appears because the current task includes {', '.join(files)}, "
            f"and {source} also changed that file recently."
        )

    return f"This appears because {signal.source_display} matches the current task scope."


def _source_label(signal: SourceSignal) -> str:
    if signal.source_display.startswith("GitHub PR"):
        return "GitHub PR metadata"
    if signal.source_display.startswith("GitLab MR"):
        return "GitLab MR metadata"
    return signal.source_display


def _scope_label(fixture: Fixture, signal: SourceSignal) -> str:
    files = _files(signal)
    service = fixture.scope.get("service")
    parts: list[str] = []
    if isinstance(service, str):
        parts.append(service)
    parts.extend(files)
    return ", ".join(parts) if parts else "current task"


def _agent_visibility(signal: SourceSignal) -> str:
    if signal.policy.can_render_to_agent:
        return "shown as evidence, not instruction"
    return "not shown unless used in this session"


def _files(signal: SourceSignal) -> list[str]:
    files = signal.scope.get("files")
    if isinstance(files, list):
        return [file for file in files if isinstance(file, str)]
    return []


def _render_generic_why(source: str) -> str:
    return (
        "Show why\n\n"
        f"This appears because {source} matches the current task scope.\n"
    )
