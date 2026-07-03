"""Forge-review metadata normalization.

Connectors fetch provider payloads; this module turns allowed PR/MR metadata into
Core Contract V0 objects. It does not fetch network data and does not render
terminal cards directly.
"""

from __future__ import annotations

from collections.abc import Iterable
from dataclasses import dataclass
from typing import Literal

from teamctx.connectors._contract import metadata_only_policy, source_status, unavailable_document
from teamctx.core.contracts import (
    ContextCard,
    CoreContractDocument,
    RequestContext,
    Scope,
    SourceFamily,
    SourceOpenTarget,
    SourceSignal,
    SourceStatus,
    SourceStatusValue,
    SourceStatusVisibility,
)

ForgeProvider = Literal["github", "gitlab"]

_SIGNAL_POLICY_REASON = (
    "Forge-review metadata is allowed as evidence; source bodies are not included."
)
_STATUS_POLICY_REASON = "Source health can render without source body text."
_SOURCE_FAMILY: SourceFamily = "git_hosting"


@dataclass(frozen=True)
class ForgeReviewPullRequest:
    provider: ForgeProvider
    repo: str
    number: int
    state: str
    url: str
    title: str | None
    changed_paths: tuple[str, ...]
    created_at: str
    updated_at: str
    merged_at: str | None = None
    labels: tuple[str, ...] = ()
    head_ref: str | None = None
    head_repo: str | None = None


def normalize_forge_review_prs(
    request_context: RequestContext,
    pull_requests: Iterable[ForgeReviewPullRequest],
    *,
    observed_at: str,
    expires_at: str = "next_refresh",
    source_id: str = "github_pr_metadata",
    coverage_truncated: bool = False,
) -> CoreContractDocument:
    source_signals: list[SourceSignal] = []
    source_open_targets: list[SourceOpenTarget] = []
    context_cards: list[ContextCard] = []
    requested_paths = set(request_context.paths)
    own_branch_prs: list[int] = []

    for pr in pull_requests:
        overlap = sorted(requested_paths.intersection(pr.changed_paths))
        if not overlap:
            continue
        if (
            request_context.branch is not None
            and pr.head_ref == request_context.branch
            and pr.head_repo == pr.repo
        ):
            own_branch_prs.append(pr.number)
            continue

        signal_id = f"sig_{pr.provider}_pr_{pr.number}_collision"
        open_target_id = f"open_{pr.provider}_pr_{pr.number}"
        source_display = f"{provider_name(pr.provider)} PR #{pr.number}"
        evidence_summary = collision_summary(pr.number, overlap)
        scope: Scope = {
            "repo": pr.repo,
            "pr_number": pr.number,
            "state": pr.state,
            "url": pr.url,
            "files": overlap,
        }
        if pr.title is not None:
            scope["title"] = pr.title
        if pr.labels:
            scope["labels"] = list(pr.labels)

        policy = metadata_only_policy(_SIGNAL_POLICY_REASON)
        source_signals.append(
            SourceSignal(
                schema_version="teamctx.source_signal.v0",
                id=signal_id,
                signal_type="collision",
                source_family="git_hosting",
                scope=scope,
                evidence_summary=evidence_summary,
                source_display=source_display,
                freshness="fresh",
                confidence="high",
                visibility="visible",
                created_at=pr.created_at,
                observed_at=observed_at,
                expires_at=expires_at,
                policy=policy,
            )
        )
        source_open_targets.append(
            SourceOpenTarget(
                schema_version="teamctx.source_open_target.v0",
                id=open_target_id,
                source_signal_id=signal_id,
                source_family="git_hosting",
                source_display=source_display,
                open_label="Open PR",
                body_availability="status_only",
                policy=policy,
            )
        )
        context_cards.append(
            ContextCard(
                schema_version="teamctx.context_card.v0",
                id=f"card_{pr.provider}_pr_{pr.number}_collision",
                section="Needs attention",
                text=evidence_summary,
                why_this_matters=why_collision_matters(overlap),
                source_display=source_display,
                refs=[signal_id],
                reason="same repository and file path as the current task",
                scope={"repo": pr.repo, "files": overlap},
                freshness="fresh",
                confidence="high",
                source_body="status_only",
                source_open_target_id=open_target_id,
                agent_instruction="verify_before_relying",
            )
        )

    status: SourceStatusValue = "stale" if coverage_truncated else "fresh"
    messages: list[str] = []
    if coverage_truncated:
        messages.append(
            "Checked the most recent 100 open PRs; there are more open PRs not included, "
            "so this is not a complete check."
        )
    if own_branch_prs:
        numbers = ", ".join(f"#{number}" for number in own_branch_prs)
        plural = "PRs" if len(own_branch_prs) > 1 else "PR"
        messages.append(
            f"Your own open {plural} {numbers} for this branch touches these files; "
            "not flagged as a collision."
        )
    if not messages:
        messages.append("Git-host PR metadata refreshed.")
    safe_user_message = " ".join(messages)
    extra_scope: Scope | None = None
    if own_branch_prs:
        extra_scope = {"own_branch_prs": [str(number) for number in own_branch_prs]}
    visibility: SourceStatusVisibility = (
        "warning_when_relevant" if own_branch_prs else "silent"
    )
    source_statuses = [
        forge_review_source_status(
            source_id=source_id,
            provider="github",
            repo=request_context.repo,
            status=status,
            observed_at=observed_at,
            safe_user_message=safe_user_message,
            visibility=visibility,
            extra_scope=extra_scope,
        )
    ]
    return CoreContractDocument(
        schema_version="teamctx.core_contract_document.v0",
        request_context=request_context,
        source_signals=source_signals,
        source_statuses=source_statuses,
        source_open_targets=source_open_targets,
        guidance_records=[],
        session_context_uses=[],
        context_cards=context_cards,
    )


def unavailable_forge_review_document(
    request_context: RequestContext,
    *,
    provider: ForgeProvider,
    repo: str,
    observed_at: str,
    source_id: str = "github_pr_metadata",
    status: SourceStatusValue = "unavailable",
    safe_user_message: str,
) -> CoreContractDocument:
    return unavailable_document(
        request_context,
        source_id=source_id,
        source_family=_SOURCE_FAMILY,
        scope={"provider": provider, "repo": repo},
        observed_at=observed_at,
        status=status,
        safe_user_message=safe_user_message,
        policy_reason=_STATUS_POLICY_REASON,
    )


def forge_review_source_status(
    *,
    source_id: str,
    provider: ForgeProvider,
    repo: str,
    status: SourceStatusValue,
    observed_at: str,
    safe_user_message: str,
    visibility: SourceStatusVisibility,
    extra_scope: Scope | None = None,
) -> SourceStatus:
    scope: Scope = {"provider": provider, "repo": repo}
    if extra_scope is not None:
        scope.update(extra_scope)
    return source_status(
        source_id=source_id,
        source_family=_SOURCE_FAMILY,
        scope=scope,
        status=status,
        observed_at=observed_at,
        safe_user_message=safe_user_message,
        visibility=visibility,
        policy_reason=_STATUS_POLICY_REASON,
    )


def collision_summary(pr_number: int, paths: list[str]) -> str:
    if len(paths) == 1:
        return f"Open PR #{pr_number} changed {paths[0]}."
    return f"Open PR #{pr_number} changed {len(paths)} files in the current task."


def why_collision_matters(paths: list[str]) -> str:
    if len(paths) == 1:
        return "you are editing the same file."
    return "you are editing the same files."


def provider_name(provider: ForgeProvider) -> str:
    if provider == "github":
        return "GitHub"
    return "GitLab"
