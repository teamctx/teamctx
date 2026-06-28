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

from teamctx.connectors.docs import run_docs_supersession_probe
from teamctx.connectors.github import run_github_pr_probe
from teamctx.connectors.github_checks import run_github_checks_probe
from teamctx.connectors.github_issues import run_github_issues_probe
from teamctx.core.contracts import CoreContractDocument, RequestContext


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
    docs_root: str | None = None
    ref: str | None = None


def build_request_context(inputs: WorkStartInputs, *, observed_at: str) -> RequestContext:
    return RequestContext(
        schema_version="teamctx.request_context.v0",
        request_id=f"work-start:{inputs.repo}:{observed_at}",
        repo=inputs.repo,
        branch=inputs.branch,
        task=inputs.task,
        paths=list(inputs.paths),
        linked_issues=list(inputs.issues),
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
    documents: list[CoreContractDocument] = [
        run_github_pr_probe(
            repo=inputs.repo,
            token=inputs.token,
            request_context=request_context,
            observed_at=observed_at,
            include_titles=inputs.include_titles,
        )
    ]

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

    return request_context, documents
