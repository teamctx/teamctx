"""Verifiable replay (Theorem 1): a content-addressed digest binding the broker's inputs.

The digest is a deterministic function of the canonical serialization of the request, the
observed signals and statuses, and the governance declarations. Same inputs → same digest →
same answer; a verifier re-derives and confirms the binding. Pure: ``json`` + ``hashlib``
are deterministic and do no I/O (the core purity test bans only os/pathlib/time/etc.).
"""

from __future__ import annotations

import hashlib
import json
from collections.abc import Iterable
from dataclasses import asdict
from typing import Any

from teamctx.core.authority import AuthorityDecl
from teamctx.core.contracts import RequestContext, SourceSignal, SourceStatus


def snapshot_digest(
    request: RequestContext,
    signals: Iterable[SourceSignal],
    statuses: Iterable[SourceStatus],
    declarations: Iterable[AuthorityDecl],
) -> str:
    """A sha256 hex digest binding the exact inputs that produced an answer (order-independent
    for the source/declaration sets)."""

    payload: dict[str, Any] = {
        "request": request.model_dump(mode="json"),
        "signals": sorted(
            (signal.model_dump(mode="json") for signal in signals), key=lambda item: item["id"]
        ),
        "statuses": sorted(
            (status.model_dump(mode="json") for status in statuses),
            key=lambda item: item["source_id"],
        ),
        "declarations": sorted(
            (asdict(decl) for decl in declarations),
            key=lambda item: (item["subject"], item["source"]),
        ),
    }
    canonical = json.dumps(payload, sort_keys=True, separators=(",", ":"))
    return hashlib.sha256(canonical.encode("utf-8")).hexdigest()
