"""Connector orchestration for a unified work-start.

Runs every connector the caller has given the means to reach, against ONE shared request
context, and returns their documents for the broker to compose. A connector is only run
when its required inputs are present, so a source we cannot reach is honestly absent from
coverage (the broker reports it Unknown) rather than silently treated as clear.

Does network/file I/O (via the connectors), so it lives outside the pure core.
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Literal

from teamctx.connectors._contract import unavailable_document
from teamctx.connectors.docs import run_docs_supersession_probe
from teamctx.connectors.github import run_github_pr_probe
from teamctx.connectors.github_checks import run_github_checks_probe
from teamctx.connectors.github_issues import run_github_issues_probe
from teamctx.core.contracts import CoreContractDocument, RequestContext, SourceFamily
from teamctx.git_context import ForgeProvider, parse_github_repo, parse_gitlab_repo

_CRITERIA_NO_ISSUE = (
    "spec changes (no issue could be derived from your branch or commits; name one with --issue)"
)
_CRITERIA_NO_SINCE = (
    "spec changes (issue {refs} was derived, but the start time couldn't be; pass --since)"
)
_CAP_NOTE = "capped at 5 issues; pass --issue to name others"
_DOCS_DISABLED = "docs (no docs root is configured; set work_start.docs_root to enable)"
_GATE_DISABLED = "failing checks (couldn't determine your branch; pass --branch or --ref)"
_GITLAB_UNWIRED_NOTE = (
    "open MRs and pipeline state (this repo is on GitLab; the GitLab connector isn't wired yet, "
    "next slice)"
)
_GITLAB_UNWIRED_MESSAGE = (
    "This repo is on GitLab. The GitLab connector isn't wired yet; open MRs and pipeline state "
    "are not checked."
)


@dataclass(frozen=True)
class WorkStartInputs:
    """Everything a unified work-start might check. Optional inputs gate optional connectors:
    omit ``issues``/``since`` and the issue tracker is not checked (criteria stays Unknown);
    omit ``docs_root`` and docs are not checked; omit a resolvable ``ref`` and gates are not
    checked. Collision is always attempted from ``repo`` + ``paths``."""

    repo: str
    paths: tuple[str, ...]
    branch: str | None = None
    task: str = "Start work."
    token: str | None = None
    include_titles: bool = False
    issues: tuple[str, ...] = ()
    since: str | None = None
    input_provenance: tuple[tuple[str, str], ...] = ()
    derived_issues_capped: bool = False
    docs_root: str | None = None
    ref: str | None = None
    forge: ForgeProvider = "github"
    profile: Literal["full", "reflex"] = "full"

    def __post_init__(self) -> None:
        normalized = _parse_repo_for_forge(self.repo, self.forge)
        if normalized is None:
            raise ValueError(f"not a valid {self.forge} repo slug: {self.repo!r}")
        object.__setattr__(self, "repo", normalized)


def build_request_context(inputs: WorkStartInputs, *, observed_at: str) -> RequestContext:
    return RequestContext(
        schema_version="teamctx.request_context.v0",
        request_id=f"work-start:{inputs.repo}:{observed_at}",
        repo=inputs.repo,
        branch=inputs.branch,
        task=inputs.task,
        paths=list(inputs.paths),
        linked_issues=list(inputs.issues),
        input_provenance=dict(inputs.input_provenance),
        requested_at=observed_at,
        requesting_principal=None,
    )


def run_work_start_connectors(
    inputs: WorkStartInputs,
    *,
    observed_at: str,
    project_root: Path = Path("."),
) -> tuple[RequestContext, list[CoreContractDocument]]:
    """Run each applicable connector against one shared request context.

    Returns the request context and the list of connector documents (one per source checked).
    The broker composes these; sources not checked here are simply absent, giving honest coverage
    rather than a false all-clear."""

    request_context = build_request_context(inputs, observed_at=observed_at)
    max_pages = 1 if inputs.profile == "reflex" else 3
    documents: list[CoreContractDocument] = []
    if inputs.forge == "gitlab":
        documents.extend(_gitlab_unwired_documents(request_context, observed_at=observed_at))
    else:
        documents.append(
            run_github_pr_probe(
                repo=inputs.repo,
                token=inputs.token,
                request_context=request_context,
                observed_at=observed_at,
                include_titles=inputs.include_titles,
                max_pages=max_pages,
            )
        )

        gate_ref = inputs.ref or inputs.branch
        if gate_ref:
            documents.append(
                run_github_checks_probe(
                    repo=inputs.repo,
                    ref=gate_ref,
                    token=inputs.token,
                    request_context=request_context,
                    observed_at=observed_at,
                )
            )
        else:
            documents.append(
                _disabled_document(
                    request_context,
                    source_id="github_check_runs",
                    source_family="ci_deploy",
                    observed_at=observed_at,
                    safe_user_message=_GATE_DISABLED,
                )
            )

    if inputs.issues and inputs.since:
        documents.append(
            run_github_issues_probe(
                repo=inputs.repo,
                issues=list(inputs.issues),
                since=inputs.since,
                token=inputs.token,
                request_context=request_context,
                observed_at=observed_at,
            )
        )
    else:
        documents.append(
            _disabled_document(
                request_context,
                source_id="github_issues",
                source_family="issue_tracker",
                observed_at=observed_at,
                safe_user_message=_criteria_disabled_message(inputs),
            )
        )

    if inputs.docs_root:
        documents.append(
            run_docs_supersession_probe(
                repo=inputs.repo,
                root=inputs.docs_root,
                request_context=request_context,
                observed_at=observed_at,
                base_dir=project_root,
            )
        )
    else:
        documents.append(
            _disabled_document(
                request_context,
                source_id="docs_supersession",
                source_family="docs",
                observed_at=observed_at,
                safe_user_message=_DOCS_DISABLED,
            )
        )

    return request_context, documents


def _disabled_document(
    request_context: RequestContext,
    *,
    source_id: str,
    source_family: SourceFamily,
    observed_at: str,
    safe_user_message: str,
    policy_reason: str = "Source was not checked because required work-start input was absent.",
) -> CoreContractDocument:
    return unavailable_document(
        request_context,
        source_id=source_id,
        source_family=source_family,
        scope={"repo": request_context.repo},
        observed_at=observed_at,
        status="disabled",
        safe_user_message=safe_user_message,
        visibility="warning_when_relevant",
        policy_reason=policy_reason,
    )


def _criteria_disabled_message(inputs: WorkStartInputs) -> str:
    if not inputs.issues:
        return _CRITERIA_NO_ISSUE
    refs = ", ".join(inputs.issues)
    message = _CRITERIA_NO_SINCE.format(refs=refs)
    if inputs.derived_issues_capped:
        message = f"{message[:-1]}; {_CAP_NOTE})"
    return message


def _parse_repo_for_forge(repo: str, forge: ForgeProvider) -> str | None:
    if forge == "github":
        return parse_github_repo(repo)
    return parse_gitlab_repo(repo)


def _gitlab_unwired_documents(
    request_context: RequestContext, *, observed_at: str
) -> list[CoreContractDocument]:
    return [
        _disabled_document(
            request_context,
            source_id="gitlab_mr_metadata",
            source_family="git_hosting",
            observed_at=observed_at,
            safe_user_message=_GITLAB_UNWIRED_NOTE,
            policy_reason=_GITLAB_UNWIRED_MESSAGE,
        ),
        _disabled_document(
            request_context,
            source_id="gitlab_pipeline_state",
            source_family="ci_deploy",
            observed_at=observed_at,
            safe_user_message=_GITLAB_UNWIRED_NOTE,
            policy_reason=_GITLAB_UNWIRED_MESSAGE,
        ),
    ]
