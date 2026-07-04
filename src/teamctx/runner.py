"""Connector orchestration for a unified work-start.

Runs every connector the caller has given the means to reach, against ONE shared request
context, and returns their documents for the broker to compose. A connector is only run
when its required inputs are present, so a source we cannot reach is honestly absent from
coverage (the broker reports it Unknown) rather than silently treated as clear.

Does network/file I/O (via the connectors), so it lives outside the pure core.
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from pathlib import Path
from typing import Literal

from teamctx.connectors._contract import unavailable_document
from teamctx.connectors.confluence import run_confluence_docs_probe
from teamctx.connectors.docs import run_docs_supersession_probe
from teamctx.connectors.docs_supersession import unavailable_docs_document
from teamctx.connectors.github import run_github_pr_probe
from teamctx.connectors.github_checks import run_github_checks_probe
from teamctx.connectors.github_issues import run_github_issues_probe
from teamctx.connectors.gitlab import run_gitlab_mr_probe, run_gitlab_pipeline_probe
from teamctx.connectors.issue_criteria import unavailable_issues_document
from teamctx.connectors.jira import run_jira_issues_probe
from teamctx.core.contracts import CoreContractDocument, RequestContext, SourceFamily
from teamctx.git_context import ForgeProvider, parse_github_repo, parse_gitlab_repo
from teamctx.tokens import resolve_token

_JIRA_KEY = re.compile(r"^[A-Z][A-Z0-9]+-\d{1,6}$", re.IGNORECASE)
_FORGE_ISSUE = re.compile(r"^#?\d{1,6}$")
_CRITERIA_NO_ISSUE = (
    "spec changes (no issue could be derived from your branch or commits; name one with --issue)"
)
_CRITERIA_NO_SINCE = (
    "spec changes (issue {refs} was derived, but the start time couldn't be; pass --since)"
)
_CAP_NOTE = "capped at 5 issues; pass --issue to name others"
_DOCS_DISABLED = "docs (no docs root is configured; set work_start.docs_root to enable)"
_GATE_DISABLED = "failing checks (couldn't determine your branch; pass --branch or --ref)"
_GITLAB_GATE_DISABLED = (
    "pipeline state (couldn't determine your branch; pass --branch or --ref)"
)
_GITLAB_ISSUES_DISABLED = (
    "spec changes (this repo is on GitLab; GitLab issue tracking isn't wired yet)"
)
_GITLAB_ISSUES_MESSAGE = (
    "This repo is on GitLab. GitLab issue tracking isn't wired yet; issue changes are not checked."
)
_JIRA_UNCONFIGURED = (
    "issue {refs} looks like a Jira issue, but no Jira is configured; add work_start.jira to "
    ".teamctx/config.json"
)
_JIRA_HALF_CREDENTIAL = (
    "Jira is configured but only half the Atlassian credential is set; both ATLASSIAN_EMAIL "
    "and ATLASSIAN_API_TOKEN are needed."
)
_CONFLUENCE_REFLEX_SKIP = (
    "Confluence docs are skipped in the quick pre-edit check; run teamctx work-start for the "
    "full scan."
)
_CONFLUENCE_HALF_CREDENTIAL = (
    "Confluence is configured but only half the Atlassian credential is set; both ATLASSIAN_EMAIL "
    "and ATLASSIAN_API_TOKEN are needed."
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
    jira_base_url: str | None = None
    confluence_base_url: str | None = None
    confluence_space_key: str | None = None
    atlassian_auth: tuple[str, str] | None = None
    atlassian_auth_missing_half: bool = False

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
        forge=inputs.forge,
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
    gitlab_diff_limit = 20 if inputs.profile == "reflex" else 100
    documents: list[CoreContractDocument] = []
    if inputs.forge == "gitlab":
        gitlab_token = resolve_token("GITLAB_TOKEN")
        documents.append(
            run_gitlab_mr_probe(
                repo=inputs.repo,
                token=gitlab_token,
                request_context=request_context,
                observed_at=observed_at,
                max_pages=max_pages,
                diff_limit=gitlab_diff_limit,
            )
        )

        gate_ref = inputs.ref or inputs.branch
        if gate_ref:
            documents.append(
                run_gitlab_pipeline_probe(
                    repo=inputs.repo,
                    ref=gate_ref,
                    token=gitlab_token,
                    request_context=request_context,
                    observed_at=observed_at,
                )
            )
        else:
            documents.append(
                _disabled_document(
                    request_context,
                    source_id="gitlab_pipeline_state",
                    source_family="ci_deploy",
                    observed_at=observed_at,
                    safe_user_message=_GITLAB_GATE_DISABLED,
                )
            )
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

    documents.extend(_run_issue_tracker_documents(inputs, request_context, observed_at))

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

    if inputs.confluence_base_url is not None and inputs.confluence_space_key is not None:
        documents.append(
            _run_confluence_document(
                inputs,
                request_context,
                observed_at,
                base_url=inputs.confluence_base_url,
                space_key=inputs.confluence_space_key,
            )
        )

    return request_context, documents


def _run_confluence_document(
    inputs: WorkStartInputs,
    request_context: RequestContext,
    observed_at: str,
    *,
    base_url: str,
    space_key: str,
) -> CoreContractDocument:
    """Confluence sits beside local docs in the same ``docs`` family. In the quick reflex profile
    it is skipped (its remote fetch is too slow for a pre-edit check) and reported as a disabled
    docs source, so the skip is honest and never reads as a clean scan. A half-set Atlassian
    credential is named before any fetch; the connector itself names a fully-missing credential."""

    if inputs.profile == "reflex":
        return _disabled_document(
            request_context,
            source_id="confluence_pages",
            source_family="docs",
            observed_at=observed_at,
            safe_user_message=_CONFLUENCE_REFLEX_SKIP,
        )
    if inputs.atlassian_auth_missing_half:
        return unavailable_docs_document(
            request_context,
            repo=request_context.repo,
            observed_at=observed_at,
            source_id="confluence_pages",
            status="unavailable",
            safe_user_message=_CONFLUENCE_HALF_CREDENTIAL,
        )
    return run_confluence_docs_probe(
        base_url=base_url,
        space_key=space_key,
        auth=inputs.atlassian_auth,
        request_context=request_context,
        observed_at=observed_at,
    )


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


def _run_issue_tracker_documents(
    inputs: WorkStartInputs, request_context: RequestContext, observed_at: str
) -> list[CoreContractDocument]:
    forge_issues, jira_issues = _split_issue_refs(inputs.issues)
    if not inputs.issues:
        return [
            _disabled_document(
                request_context,
                source_id="github_issues" if inputs.forge == "github" else "gitlab_issues",
                source_family="issue_tracker",
                observed_at=observed_at,
                safe_user_message=_CRITERIA_NO_ISSUE,
            )
        ]

    documents: list[CoreContractDocument] = []
    if forge_issues:
        if inputs.since:
            if inputs.forge == "gitlab":
                documents.append(
                    _disabled_document(
                        request_context,
                        source_id="gitlab_issues",
                        source_family="issue_tracker",
                        observed_at=observed_at,
                        safe_user_message=_GITLAB_ISSUES_DISABLED,
                        policy_reason=_GITLAB_ISSUES_MESSAGE,
                    )
                )
            else:
                documents.append(
                    run_github_issues_probe(
                        repo=inputs.repo,
                        issues=list(forge_issues),
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
                    source_id="github_issues" if inputs.forge == "github" else "gitlab_issues",
                    source_family="issue_tracker",
                    observed_at=observed_at,
                    safe_user_message=_criteria_no_since_message(inputs, forge_issues),
                )
            )

    if jira_issues:
        if inputs.jira_base_url is None:
            documents.append(
                _disabled_document(
                    request_context,
                    source_id="jira_issues",
                    source_family="issue_tracker",
                    observed_at=observed_at,
                    safe_user_message=_JIRA_UNCONFIGURED.format(
                        refs=", ".join(jira_issues)
                    ),
                )
            )
        elif not inputs.since:
            documents.append(
                _disabled_document(
                    request_context,
                    source_id="jira_issues",
                    source_family="issue_tracker",
                    observed_at=observed_at,
                    safe_user_message=_criteria_no_since_message(inputs, jira_issues),
                )
            )
        elif inputs.atlassian_auth_missing_half:
            documents.append(
                unavailable_issues_document(
                    request_context,
                    repo=request_context.repo,
                    observed_at=observed_at,
                    source_id="jira_issues",
                    safe_user_message=_JIRA_HALF_CREDENTIAL,
                )
            )
        else:
            documents.append(
                run_jira_issues_probe(
                    base_url=inputs.jira_base_url,
                    issues=list(jira_issues),
                    since=inputs.since,
                    auth=inputs.atlassian_auth,
                    request_context=request_context,
                    observed_at=observed_at,
                )
            )

    if documents:
        return documents
    return [
        _disabled_document(
            request_context,
            source_id="github_issues" if inputs.forge == "github" else "gitlab_issues",
            source_family="issue_tracker",
            observed_at=observed_at,
            safe_user_message=_CRITERIA_NO_ISSUE,
        )
    ]


def _split_issue_refs(issues: tuple[str, ...]) -> tuple[tuple[str, ...], tuple[str, ...]]:
    forge_issues: list[str] = []
    jira_issues: list[str] = []
    for issue in issues:
        if _FORGE_ISSUE.fullmatch(issue):
            forge_issues.append(issue)
        elif _JIRA_KEY.fullmatch(issue):
            jira_issues.append(issue.upper())
    return tuple(forge_issues), tuple(jira_issues)


def _criteria_disabled_message(inputs: WorkStartInputs) -> str:
    if not inputs.issues:
        return _CRITERIA_NO_ISSUE
    return _criteria_no_since_message(inputs, inputs.issues)


def _criteria_no_since_message(inputs: WorkStartInputs, refs: tuple[str, ...]) -> str:
    refs_text = ", ".join(refs)
    message = _CRITERIA_NO_SINCE.format(refs=refs_text)
    if inputs.derived_issues_capped:
        message = f"{message[:-1]}; {_CAP_NOTE})"
    return message


def _parse_repo_for_forge(repo: str, forge: ForgeProvider) -> str | None:
    if forge == "github":
        return parse_github_repo(repo)
    return parse_gitlab_repo(repo)
