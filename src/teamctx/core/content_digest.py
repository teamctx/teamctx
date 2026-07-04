"""Content identity for ambient baselines.

This digest is deliberately narrower than the replay snapshot digest: it binds only the facts
that should make the hook speak again. Volatile timing fields and already-spoken delta signals stay
out, so a stable answer remains stable across re-checks.
"""

from __future__ import annotations

import hashlib
import json
from collections.abc import Iterable
from typing import Any

from teamctx.core.authority import AuthorityEntry
from teamctx.core.contracts import SourceSignal, SourceStatus
from teamctx.core.select import ClosureEntry


def content_digest(
    signals: Iterable[SourceSignal],
    statuses: Iterable[SourceStatus],
    closure: Iterable[ClosureEntry],
    authority: Iterable[AuthorityEntry],
) -> str:
    """Return a sha256 hex digest for the current pre-delta answer's decision-bearing content."""

    payload = {
        "signals": _sorted_items(_signal_item(signal) for signal in signals),
        "statuses": _sorted_items(_status_item(status) for status in statuses),
        "closure": _sorted_items(_closure_item(entry) for entry in closure),
        "authority": _sorted_items(_authority_item(entry) for entry in authority),
    }
    canonical = json.dumps(payload, sort_keys=True, separators=(",", ":"))
    return hashlib.sha256(canonical.encode("utf-8")).hexdigest()


def _signal_item(signal: SourceSignal) -> dict[str, Any] | None:
    if signal.signal_type == "changed_since_start":
        return None
    return {
        "signal_type": signal.signal_type,
        "source_family": signal.source_family,
        "scope": signal.scope,
        "evidence_summary": signal.evidence_summary,
        "source_display": signal.source_display,
        "freshness": signal.freshness,
        "confidence": signal.confidence,
        "visibility": signal.visibility,
    }


def _status_item(status: SourceStatus) -> dict[str, Any]:
    return {
        "source_id": status.source_id,
        "source_family": status.source_family,
        "status": status.status,
        "normal_context_visibility": status.normal_context_visibility,
    }


def _closure_item(entry: ClosureEntry) -> dict[str, str]:
    return {"proposition": entry.proposition, "status": entry.status}


def _authority_item(entry: AuthorityEntry) -> dict[str, str | None]:
    return {"subject": entry.subject, "state": entry.state, "value": entry.value}


def _sorted_items(items: Iterable[dict[str, Any] | None]) -> list[dict[str, Any]]:
    serialized = [
        json.dumps(item, sort_keys=True, separators=(",", ":"))
        for item in items
        if item is not None
    ]
    return [json.loads(item) for item in sorted(serialized)]
