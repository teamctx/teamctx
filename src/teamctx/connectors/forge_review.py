"""Forge-review metadata normalization.

Connectors fetch provider payloads; this module turns allowed PR/MR metadata into
Core Contract V0 objects. It does not fetch network data and does not render
terminal cards directly.
"""

from __future__ import annotations

from collections.abc import Iterable
from dataclasses import dataclass
from typing import Literal

from teamctx.connectors._contract import (
    document_identity,
    metadata_only_policy,
    source_status,
    unavailable_document,
)
from teamctx.core.contracts import (
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
from teamctx.core.kinds import FORGE_REVIEW_SOURCE_CONTRACT

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
    source_project_id: int | None = None
    target_project_id: int | None = None


def normalize_forge_review_prs(
    request_context: RequestContext,
    pull_requests: Iterable[ForgeReviewPullRequest],
    *,
    observed_at: str,
    expires_at: str = "next_refresh",
    provider: ForgeProvider = "github",
    source_id: str = "github_pr_metadata",
    coverage_unbounded_list: bool = False,
    unbounded_files_prs: Iterable[int] = (),
    diff_checked_count: int | None = None,
    diff_unchecked_count: int = 0,
) -> CoreContractDocument:
    source_signals: list[SourceSignal] = []
    source_open_targets: list[SourceOpenTarget] = []
    requested_paths = set(request_context.paths)
    own_branch_prs: list[int] = []
    pull_request_list = list(pull_requests)
    unbounded_file_pr_numbers = set(unbounded_files_prs)
    relevant_unbounded_files_prs: list[int] = []

    for pr in pull_request_list:
        overlap = sorted(requested_paths.intersection(pr.changed_paths))
        if _is_own_branch_review(pr, request_context.branch):
            if overlap:
                own_branch_prs.append(pr.number)
            continue
        if not overlap:
            if pr.number in unbounded_file_pr_numbers:
                relevant_unbounded_files_prs.append(pr.number)
            continue

        review = review_terms(pr.provider)
        signal_id = f"sig_{pr.provider}_{review.id_part}_{pr.number}_collision"
        open_target_id = f"open_{pr.provider}_{review.id_part}_{pr.number}"
        source_display = source_display_for(pr.provider, pr.number)
        evidence_summary = collision_summary(pr.provider, pr.number, overlap)
        scope: Scope = {
            "provider": pr.provider,
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
                open_label=f"Open {review.short}",
                body_availability="status_only",
                policy=policy,
            )
        )

    coverage_unbounded = (
        coverage_unbounded_list or bool(relevant_unbounded_files_prs) or bool(diff_unchecked_count)
    )
    status: SourceStatusValue = "unbounded" if coverage_unbounded else "fresh"
    messages: list[str] = []
    if coverage_unbounded_list:
        review = review_terms(provider)
        copy = FORGE_REVIEW_SOURCE_CONTRACT.advisory_copy
        messages.append(
            copy.unbounded_page.format(count=len(pull_request_list), plural=review.plural)
        )
    if diff_unchecked_count and diff_checked_count is not None:
        review = review_terms(provider)
        copy = FORGE_REVIEW_SOURCE_CONTRACT.advisory_copy
        messages.append(
            copy.unbounded_diff.format(
                checked_count=diff_checked_count,
                unchecked_count=diff_unchecked_count,
                plural=review.plural,
            )
        )
    for number in relevant_unbounded_files_prs:
        review = review_terms(provider)
        copy = FORGE_REVIEW_SOURCE_CONTRACT.advisory_copy
        messages.append(
            copy.unbounded_files.format(
                short=review.short,
                prefix=review.prefix,
                number=number,
            )
        )
    if own_branch_prs:
        review = review_terms(provider)
        copy = FORGE_REVIEW_SOURCE_CONTRACT.advisory_copy
        numbers = ", ".join(f"{review.prefix}{number}" for number in own_branch_prs)
        if len(own_branch_prs) > 1:
            messages.append(
                copy.own_branch_multiple.format(plural=review.plural, numbers=numbers)
            )
        else:
            messages.append(
                copy.own_branch_single.format(short=review.short, numbers=numbers)
            )
    if not messages:
        copy = FORGE_REVIEW_SOURCE_CONTRACT.advisory_copy
        messages.append(copy.fresh.format(short=review_terms(provider).short))
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
            provider=provider,
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
        **document_identity(source_id=source_id, source_family=_SOURCE_FAMILY),
        request_context=request_context,
        source_signals=source_signals,
        source_statuses=source_statuses,
        source_open_targets=source_open_targets,
        guidance_records=[],
        session_context_uses=[],
        context_cards=[],
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


def collision_summary(provider: ForgeProvider, number: int, paths: list[str]) -> str:
    review = review_terms(provider)
    if len(paths) == 1:
        return f"Open {review.short} {review.prefix}{number} changed {paths[0]}."
    return (
        f"Open {review.short} {review.prefix}{number} changed {len(paths)} files in the "
        "current task."
    )


def provider_name(provider: ForgeProvider) -> str:
    if provider == "github":
        return "GitHub"
    return "GitLab"


@dataclass(frozen=True)
class ReviewTerms:
    short: str
    plural: str
    prefix: str
    id_part: str


def review_terms(provider: ForgeProvider) -> ReviewTerms:
    if provider == "github":
        return ReviewTerms(short="PR", plural="PRs", prefix="#", id_part="pr")
    return ReviewTerms(short="MR", plural="MRs", prefix="!", id_part="mr")


def source_display_for(provider: ForgeProvider, number: int) -> str:
    review = review_terms(provider)
    return f"{provider_name(provider)} {review.short} {review.prefix}{number}"


def _is_own_branch_review(pr: ForgeReviewPullRequest, branch: str | None) -> bool:
    if branch is None or pr.head_ref != branch:
        return False
    if pr.provider == "gitlab":
        return pr.source_project_id is not None and pr.source_project_id == pr.target_project_id
    return pr.head_repo == pr.repo
