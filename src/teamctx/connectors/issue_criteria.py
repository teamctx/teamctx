"""Issue criteria-changed normalization.

Turns issue-movement facts into Core Contract V0 objects. No file/network I/O and no card
rendering — work-start DERIVES criteria-changed cards from the signals emitted here.
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

_POLICY_REASON = "Issue metadata is allowed as evidence; source bodies are not included."
_SOURCE_FAMILY: SourceFamily = "issue_tracker"


@dataclass(frozen=True)
class IssueCriteriaChange:
    """An issue linked to the current work whose criteria may have changed.

    ``issue`` uses the ``#N`` format to match ``request_context.linked_issues``.
    ``change_kinds`` categorizes what moved: body_edited, state_changed, labels_changed.
    """

    repo: str
    issue: str
    issue_url: str
    title: str
    state: str
    labels: tuple[str, ...]
    change_kinds: tuple[str, ...]
    detail: str
    updated_at: str


def normalize_issue_changes(
    request_context: RequestContext,
    changes: Iterable[IssueCriteriaChange],
    *,
    observed_at: str,
    expires_at: str = "next_refresh",
    source_id: str = "github_issues",
) -> CoreContractDocument:
    source_signals: list[SourceSignal] = []
    for index, change in enumerate(changes):
        scope: Scope = {
            "repo": change.repo,
            "issue": change.issue,
            "url": change.issue_url,
            "state": change.state,
            "change_kinds": list(change.change_kinds),
        }
        if change.labels:
            scope["labels"] = list(change.labels)

        source_signals.append(
            SourceSignal(
                schema_version="teamctx.source_signal.v0",
                id=f"sig_issue_{slug(change.issue)}_{index}",
                signal_type="criteria_changed",
                source_family=_SOURCE_FAMILY,
                scope=scope,
                evidence_summary=change.detail,
                source_display=f"GitHub Issue {change.issue}: {change.title}",
                freshness="fresh",
                confidence="high",
                visibility="visible",
                created_at=change.updated_at,
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
            safe_user_message="Issue tracker status refreshed.",
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


def unavailable_issues_document(
    request_context: RequestContext,
    *,
    repo: str,
    observed_at: str,
    source_id: str = "github_issues",
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
