"""Pure core context and contract primitives for teamctx.

One model: the contracts model below. (The retired fixture-lineage prototype model was
removed in the foundation-hardening pass — the evidence engine now tests this model via
``teamctx.eval``.)
"""

from __future__ import annotations

__all__ = [
    "ContextCard",
    "CoreContractDocument",
    "GuidanceRecord",
    "PolicyDecision",
    "RequestContext",
    "SessionContextUse",
    "SourceOpenTarget",
    "SourceSignal",
    "SourceStatus",
]

from teamctx.core.contracts import (
    ContextCard,
    CoreContractDocument,
    GuidanceRecord,
    PolicyDecision,
    RequestContext,
    SessionContextUse,
    SourceOpenTarget,
    SourceSignal,
    SourceStatus,
)
