"""Docs supersession normalization.

The docs connector reads markdown frontmatter; this module turns declared supersession
facts into Core Contract V0 objects. It does no file I/O and renders no cards directly —
work-start DERIVES doc-superseded cards from the signals emitted here.
"""

from __future__ import annotations

from collections.abc import Iterable
from dataclasses import dataclass

from teamctx.connectors._contract import (
    metadata_only_policy,
    slug,
    source_status,
    unavailable_document,
)
from teamctx.core.contracts import (
    CoreContractDocument,
    RequestContext,
    Scope,
    SourceFamily,
    SourceSignal,
    SourceStatusValue,
)

_POLICY_REASON = "Docs supersession metadata is allowed as evidence; bodies are not included."
_SOURCE_FAMILY: SourceFamily = "docs"


@dataclass(frozen=True)
class SupersededDoc:
    """A doc that declares it has been superseded, with the doc that replaces it.

    All paths are repo-root-relative POSIX strings."""

    repo: str
    doc: str
    superseded_by: str


def normalize_superseded_docs(
    request_context: RequestContext,
    docs: Iterable[SupersededDoc],
    *,
    observed_at: str,
    expires_at: str = "next_refresh",
    source_id: str = "docs_supersession",
) -> CoreContractDocument:
    source_signals: list[SourceSignal] = []
    for entry in docs:
        scope: Scope = {
            "repo": entry.repo,
            "doc": entry.doc,
            "superseded_by": entry.superseded_by,
        }
        source_signals.append(
            SourceSignal(
                schema_version="teamctx.source_signal.v0",
                id=f"sig_doc_superseded_{slug(entry.doc)}",
                signal_type="doc_superseded",
                source_family=_SOURCE_FAMILY,
                scope=scope,
                evidence_summary=f"{entry.doc} was superseded by {entry.superseded_by}.",
                source_display=entry.doc,
                freshness="fresh",
                confidence="high",
                visibility="visible",
                created_at=observed_at,
                observed_at=observed_at,
                expires_at=expires_at,
                policy=metadata_only_policy(_POLICY_REASON),
            )
        )
    source_statuses = [
        source_status(
            source_id=source_id,
            source_family=_SOURCE_FAMILY,
            scope={"repo": request_context.repo},
            status="fresh",
            observed_at=observed_at,
            safe_user_message="Docs supersession metadata refreshed.",
            visibility="silent",
            policy_reason=_POLICY_REASON,
        )
    ]
    return CoreContractDocument(
        schema_version="teamctx.core_contract_document.v0",
        request_context=request_context,
        source_signals=source_signals,
        source_statuses=source_statuses,
        source_open_targets=[],
        guidance_records=[],
        session_context_uses=[],
        context_cards=[],
    )


def unavailable_docs_document(
    request_context: RequestContext,
    *,
    repo: str,
    observed_at: str,
    source_id: str = "docs_supersession",
    status: SourceStatusValue = "unavailable",
    safe_user_message: str,
) -> CoreContractDocument:
    return unavailable_document(
        request_context,
        source_id=source_id,
        source_family=_SOURCE_FAMILY,
        scope={"repo": repo},
        observed_at=observed_at,
        status=status,
        safe_user_message=safe_user_message,
        policy_reason=_POLICY_REASON,
    )
