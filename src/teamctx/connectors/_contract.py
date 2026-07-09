"""Shared helpers for building Core Contract objects from a connector.

Every connector normalizes provider facts into the same handful of contract shapes: a
metadata-only policy, a source status, an "unavailable" document, and a slug for ids. These
were copy-pasted across the connectors; centralizing them gives one way to build contract
objects (and makes the next connector cheap). Pure: no I/O.
"""

from __future__ import annotations

from teamctx.core.contracts import (
    CoreContractDocument,
    PolicyDecision,
    RequestContext,
    Scope,
    SourceFamily,
    SourceStatus,
    SourceStatusValue,
    SourceStatusVisibility,
)


def metadata_only_policy(reason: str) -> PolicyDecision:
    """Evidence is allowed; source bodies are not. The policy every connector emits."""

    return PolicyDecision(
        schema_version="teamctx.policy_decision.v0",
        can_render_to_user=True,
        can_render_to_agent=True,
        can_include_source_text=False,
        requires_review_for_guidance=False,
        decision_reason=reason,
    )


def document_id_for_source(source_id: str) -> str:
    """Stable document id for a connector-owned source document."""

    return f"doc_{slug(source_id)}"


def document_type_for_source_family(source_family: SourceFamily) -> str:
    """The current one-check-per-document-type mapping."""

    match source_family:
        case "git_hosting":
            return "forge_review"
        case "ci_deploy":
            return "gate_status"
        case "issue_tracker":
            return "issue_criteria"
        case "docs":
            return "docs_supersession"
        case _:
            return str(source_family)


def document_identity(
    *, source_id: str, source_family: SourceFamily, document_type: str | None = None
) -> dict[str, str]:
    return {
        "document_id": document_id_for_source(source_id),
        "document_type": document_type or document_type_for_source_family(source_family),
    }


def source_status(
    *,
    source_id: str,
    source_family: SourceFamily,
    scope: Scope,
    status: SourceStatusValue,
    observed_at: str,
    safe_user_message: str,
    visibility: SourceStatusVisibility,
    policy_reason: str,
) -> SourceStatus:
    """A source-health record. ``last_checked_at`` is the observation time unless stale."""

    return SourceStatus(
        schema_version="teamctx.source_status.v0",
        source_id=source_id,
        source_family=source_family,
        scope=scope,
        status=status,
        last_checked_at=observed_at if status != "stale" else None,
        safe_user_message=safe_user_message,
        normal_context_visibility=visibility,
        policy=metadata_only_policy(policy_reason),
    )


def unavailable_document(
    request_context: RequestContext,
    *,
    source_id: str,
    source_family: SourceFamily,
    scope: Scope,
    observed_at: str,
    status: SourceStatusValue,
    safe_user_message: str,
    policy_reason: str,
    visibility: SourceStatusVisibility = "warning_when_relevant",
) -> CoreContractDocument:
    """A document carrying only a single unhealthy source status (no signals, no clearance)."""

    return CoreContractDocument(
        schema_version="teamctx.core_contract_document.v0",
        **document_identity(source_id=source_id, source_family=source_family),
        request_context=request_context,
        source_signals=[],
        source_statuses=[
            source_status(
                source_id=source_id,
                source_family=source_family,
                scope=scope,
                status=status,
                observed_at=observed_at,
                safe_user_message=safe_user_message,
                visibility=visibility,
                policy_reason=policy_reason,
            )
        ],
        source_open_targets=[],
        guidance_records=[],
        session_context_uses=[],
        context_cards=[],
    )


def slug(text: str) -> str:
    """Replace every non-alphanumeric character with ``_`` for use in stable ids."""

    return "".join(ch if ch.isalnum() else "_" for ch in text)
