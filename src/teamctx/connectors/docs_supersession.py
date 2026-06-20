"""Docs supersession normalization.

The docs connector reads markdown frontmatter; this module turns declared supersession
facts into Core Contract V0 objects. It does no file I/O and renders no cards directly —
work-start DERIVES doc-superseded cards from the signals emitted here.
"""

from __future__ import annotations

from collections.abc import Iterable
from dataclasses import dataclass
from typing import Literal

from teamctx.core.contracts import (
    CoreContractDocument,
    PolicyDecision,
    RequestContext,
    Scope,
    SourceSignal,
    SourceStatus,
    SourceStatusValue,
)


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
                id=f"sig_doc_superseded_{_slug(entry.doc)}",
                signal_type="doc_superseded",
                source_family="docs",
                scope=scope,
                evidence_summary=f"{entry.doc} was superseded by {entry.superseded_by}.",
                source_display=entry.doc,
                freshness="fresh",
                confidence="high",
                visibility="visible",
                created_at=observed_at,
                observed_at=observed_at,
                expires_at=expires_at,
                policy=_policy_metadata_only(),
            )
        )
    source_statuses = [
        _docs_source_status(
            source_id=source_id,
            repo=request_context.repo,
            status="fresh",
            observed_at=observed_at,
            safe_user_message="Docs supersession metadata refreshed.",
            visibility="silent",
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
    return CoreContractDocument(
        schema_version="teamctx.core_contract_document.v0",
        request_context=request_context,
        source_signals=[],
        source_statuses=[
            _docs_source_status(
                source_id=source_id,
                repo=repo,
                status=status,
                observed_at=observed_at,
                safe_user_message=safe_user_message,
                visibility="warning_when_relevant",
            )
        ],
        source_open_targets=[],
        guidance_records=[],
        session_context_uses=[],
        context_cards=[],
    )


def _docs_source_status(
    *,
    source_id: str,
    repo: str,
    status: SourceStatusValue,
    observed_at: str,
    safe_user_message: str,
    visibility: Literal["silent", "warning_when_relevant", "always"],
) -> SourceStatus:
    return SourceStatus(
        schema_version="teamctx.source_status.v0",
        source_id=source_id,
        source_family="docs",
        scope={"repo": repo},
        status=status,
        last_checked_at=observed_at if status != "stale" else None,
        safe_user_message=safe_user_message,
        normal_context_visibility=visibility,
        policy=_policy_metadata_only(),
    )


def _policy_metadata_only() -> PolicyDecision:
    return PolicyDecision(
        schema_version="teamctx.policy_decision.v0",
        can_render_to_user=True,
        can_render_to_agent=True,
        can_include_source_text=False,
        requires_review_for_guidance=False,
        decision_reason=(
            "Docs supersession metadata is allowed as evidence; bodies are not included."
        ),
    )


def _slug(path: str) -> str:
    return "".join(ch if ch.isalnum() else "_" for ch in path)
