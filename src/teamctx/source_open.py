"""Explicit source opening for fixture-backed context."""

from __future__ import annotations

from teamctx.core.cards import find_card, find_signal
from teamctx.core.models import Fixture, SourceArtifact, SourceSignal


class SourceOpenError(ValueError):
    """Raised when a requested source cannot be resolved."""


def render_open_source(fixture: Fixture, ref_id: str) -> str:
    signal = resolve_open_source_signal(fixture, ref_id)
    artifact = find_source_artifact(fixture, signal.id)

    lines = ["Open source", "", signal.source_display, f"Freshness: {signal.freshness}"]
    if signal.freshness == "stale":
        lines.append("Use as background only. Verify before relying.")

    unavailable_reason = source_body_unavailable_reason(signal, artifact)
    if unavailable_reason is not None:
        lines.extend(["", "Source body unavailable.", f"Reason: {unavailable_reason}"])
        return "\n".join(lines) + "\n"

    assert artifact is not None
    lines.extend(["", artifact.title, "", artifact.body.rstrip()])
    return "\n".join(lines) + "\n"


def resolve_open_source_signal(fixture: Fixture, ref_id: str) -> SourceSignal:
    signal = find_signal(fixture, ref_id)
    if signal is not None:
        return signal

    try:
        card = find_card(fixture, ref_id)
    except KeyError as exc:
        raise SourceOpenError(f"Unknown source or card id: {ref_id}") from exc

    signals = [found for ref in card.refs if (found := find_signal(fixture, ref)) is not None]
    if not signals:
        raise SourceOpenError("This card does not have an openable source.")
    return signals[0]


def find_source_artifact(fixture: Fixture, source_signal_id: str) -> SourceArtifact | None:
    for artifact in fixture.source_artifacts:
        if artifact.source_signal_id == source_signal_id:
            return artifact
    return None


def source_body_unavailable_reason(
    signal: SourceSignal, artifact: SourceArtifact | None
) -> str | None:
    if not signal.policy.can_render_to_user:
        return "TeamCtx cannot show this source."
    if signal.visibility == "never":
        return "TeamCtx cannot show this source."
    if signal.freshness == "blocked":
        return "This source is blocked by policy."
    if signal.freshness == "unavailable":
        return "This source is unavailable with current access."
    if not signal.policy.can_include_source_text:
        return "TeamCtx can show the status, but not the source body."
    if artifact is None:
        return "No source body is available for this source."
    return None
