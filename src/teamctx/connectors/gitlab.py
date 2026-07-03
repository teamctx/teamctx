"""Narrow GitLab merge-request metadata probe."""

from __future__ import annotations

import json
from collections.abc import Callable
from dataclasses import dataclass, field, replace
from email.message import Message
from typing import Protocol, Self, cast
from urllib.error import HTTPError, URLError
from urllib.parse import quote
from urllib.request import Request, urlopen

from teamctx.connectors.forge_review import (
    ForgeReviewPullRequest,
    normalize_forge_review_prs,
    unavailable_forge_review_document,
)
from teamctx.connectors.gate_status import (
    FailingGate,
    normalize_failing_gates,
    pending_gates_document,
    unavailable_gates_document,
)
from teamctx.core.contracts import CoreContractDocument, RequestContext

GITLAB_API_ROOT = "https://gitlab.com"


def gitlab_api_root() -> str:
    """The GitLab API root, env-overridable via ``TEAMCTX_GITLAB_API_ROOT`` (trailing slash
    stripped). The override exists for the emulation program: fabricated payloads can be driven
    through the REAL pipeline against a local mock server. Read at call time, never cached.
    Token-sensitive: requests to the override host carry the resolved token; this is an
    intentional local-operator seam for tests and validation harnesses only."""

    import os

    return os.environ.get("TEAMCTX_GITLAB_API_ROOT", GITLAB_API_ROOT).rstrip("/")


class HttpResponse(Protocol):
    headers: Message

    def read(self) -> bytes: ...

    def __enter__(self) -> Self: ...

    def __exit__(self, exc_type: object, exc: object, traceback: object) -> object: ...


HttpOpener = Callable[[Request], HttpResponse]
DEFAULT_OPENER = cast(HttpOpener, urlopen)


@dataclass(frozen=True)
class GitLabMRFetch:
    """Result of fetching open merge requests from GitLab."""

    merge_requests: list[ForgeReviewPullRequest]
    unbounded_list: bool = False
    unbounded_files_mrs: list[int] = field(default_factory=list)
    diff_checked_count: int = 0
    diff_unchecked_count: int = 0


@dataclass(frozen=True)
class GitLabPipeline:
    id: int
    status: str
    web_url: str


class GitLabProbeError(RuntimeError):
    def __init__(
        self,
        message: str,
        *,
        status_code: int | None = None,
        stale: bool = False,
    ) -> None:
        super().__init__(message)
        self.status_code = status_code
        self.stale = stale


_PENDING_PIPELINE_STATUSES = frozenset(
    {"running", "pending", "created", "waiting_for_resource", "preparing", "scheduled"}
)
_FAILING_PIPELINE_STATUSES = frozenset({"failed", "canceled"})
_FAILING_JOB_STATUSES = frozenset({"failed", "canceled"})
_PIPELINE_STALE_MESSAGE = "the pipeline state could not be confirmed green"
_ZERO_PIPELINES_NOTE = "no pipeline ran for this branch, so the gate is unverified"


def run_gitlab_mr_probe(
    *,
    repo: str,
    token: str | None,
    request_context: RequestContext,
    observed_at: str,
    max_pages: int = 3,
    diff_limit: int = 100,
    opener: HttpOpener = DEFAULT_OPENER,
) -> CoreContractDocument:
    if not token:
        return unavailable_forge_review_document(
            request_context,
            provider="gitlab",
            repo=repo,
            observed_at=observed_at,
            source_id="gitlab_mr_metadata",
            safe_user_message="GitLab MR metadata is unavailable because no token is configured.",
        )

    try:
        fetch = fetch_gitlab_merge_requests(
            repo=repo,
            token=token,
            request_branch=request_context.branch,
            max_pages=max_pages,
            diff_limit=diff_limit,
            opener=opener,
        )
    except GitLabProbeError as exc:
        return unavailable_forge_review_document(
            request_context,
            provider="gitlab",
            repo=repo,
            observed_at=observed_at,
            source_id="gitlab_mr_metadata",
            safe_user_message=gitlab_error_message(exc, source="GitLab MR metadata"),
        )

    return normalize_forge_review_prs(
        request_context,
        fetch.merge_requests,
        observed_at=observed_at,
        provider="gitlab",
        source_id="gitlab_mr_metadata",
        coverage_unbounded_list=fetch.unbounded_list,
        unbounded_files_prs=fetch.unbounded_files_mrs,
        diff_checked_count=fetch.diff_checked_count,
        diff_unchecked_count=fetch.diff_unchecked_count,
    )


def run_gitlab_pipeline_probe(
    *,
    repo: str,
    ref: str,
    token: str | None,
    request_context: RequestContext,
    observed_at: str,
    opener: HttpOpener = DEFAULT_OPENER,
) -> CoreContractDocument:
    if not token:
        return unavailable_gates_document(
            request_context,
            repo=repo,
            observed_at=observed_at,
            source_id="gitlab_pipeline_state",
            safe_user_message="CI status is unavailable because no token is configured.",
        )

    try:
        pipeline = fetch_latest_gitlab_pipeline(
            repo=repo, ref=ref, token=token, opener=opener
        )
        if pipeline is None:
            return unavailable_gates_document(
                request_context,
                repo=repo,
                observed_at=observed_at,
                source_id="gitlab_pipeline_state",
                status="disabled",
                safe_user_message=_ZERO_PIPELINES_NOTE,
            )
        if pipeline.status == "success":
            return normalize_failing_gates(
                request_context,
                [],
                observed_at=observed_at,
                source_id="gitlab_pipeline_state",
            )
        if pipeline.status in _PENDING_PIPELINE_STATUSES:
            return pending_gates_document(
                request_context,
                repo=repo,
                observed_at=observed_at,
                source_id="gitlab_pipeline_state",
                safe_user_message=(
                    f"GitLab pipeline is {pipeline.status}; the gate is not confirmed green yet."
                ),
            )
        if pipeline.status in _FAILING_PIPELINE_STATUSES:
            gates = fetch_gitlab_failing_pipeline_jobs(
                repo=repo, pipeline=pipeline, token=token, opener=opener
            )
            if not gates:
                gates = [(f"pipeline {pipeline.status}", pipeline.web_url)]
            return normalize_failing_gates(
                request_context,
                [
                    FailingGate(
                        repo=repo,
                        gate_name=name,
                        url=url,
                        files=tuple(request_context.paths),
                    )
                    for name, url in gates
                ],
                observed_at=observed_at,
                source_id="gitlab_pipeline_state",
            )
        return _stale_pipeline_document(request_context, repo=repo, observed_at=observed_at)
    except GitLabProbeError as exc:
        if exc.stale:
            return _stale_pipeline_document(request_context, repo=repo, observed_at=observed_at)
        return unavailable_gates_document(
            request_context,
            repo=repo,
            observed_at=observed_at,
            source_id="gitlab_pipeline_state",
            safe_user_message=gitlab_error_message(exc, source="CI status"),
        )


def fetch_gitlab_merge_requests(
    *,
    repo: str,
    token: str,
    request_branch: str | None,
    max_pages: int = 3,
    diff_limit: int = 100,
    opener: HttpOpener = DEFAULT_OPENER,
) -> GitLabMRFetch:
    if max_pages < 1:
        raise GitLabProbeError("GitLab merge-request page budget must be at least one")
    if diff_limit < 0:
        raise GitLabProbeError("GitLab merge-request diff budget cannot be negative")

    project = quote(repo, safe="")
    merge_requests: list[ForgeReviewPullRequest] = []
    unbounded_list = False
    page = 1
    for page_number in range(1, max_pages + 1):
        payload, headers = get_json_with_headers(
            f"{gitlab_api_root()}/api/v4/projects/{project}/merge_requests"
            f"?state=opened&order_by=updated_at&sort=desc&per_page=100&page={page}",
            token=token,
            opener=opener,
        )
        page_mrs = _parse_merge_request_page(repo=repo, payload=payload)
        merge_requests.extend(page_mrs)
        has_more, next_page = _pagination(headers, len(page_mrs), current_page=page)
        if not has_more:
            break
        if page_number == max_pages:
            unbounded_list = True
            break
        page = next_page

    merge_requests, unbounded_files_mrs, checked_count, unchecked_count = (
        _fetch_merge_request_diffs(
            repo=repo,
            project=project,
            token=token,
            request_branch=request_branch,
            merge_requests=merge_requests,
            diff_limit=diff_limit,
            opener=opener,
        )
    )
    return GitLabMRFetch(
        merge_requests=merge_requests,
        unbounded_list=unbounded_list,
        unbounded_files_mrs=unbounded_files_mrs,
        diff_checked_count=checked_count,
        diff_unchecked_count=unchecked_count,
    )


def fetch_latest_gitlab_pipeline(
    *, repo: str, ref: str, token: str, opener: HttpOpener = DEFAULT_OPENER
) -> GitLabPipeline | None:
    project = quote(repo, safe="")
    payload, _ = get_json_with_headers(
        f"{gitlab_api_root()}/api/v4/projects/{project}/pipelines"
        f"?ref={quote(ref, safe='')}&per_page=1&order_by=updated_at&sort=desc",
        token=token,
        opener=opener,
    )
    if not isinstance(payload, list):
        raise GitLabProbeError("GitLab pipelines response was not a list", stale=True)
    if not payload:
        return None
    return _parse_pipeline(payload[0])


def fetch_gitlab_failing_pipeline_jobs(
    *,
    repo: str,
    pipeline: GitLabPipeline,
    token: str,
    opener: HttpOpener = DEFAULT_OPENER,
) -> list[tuple[str, str]]:
    project = quote(repo, safe="")
    payload, _ = get_json_with_headers(
        f"{gitlab_api_root()}/api/v4/projects/{project}/pipelines/{pipeline.id}/jobs"
        "?per_page=100",
        token=token,
        opener=opener,
    )
    if not isinstance(payload, list):
        raise GitLabProbeError("GitLab pipeline jobs response was not a list", stale=True)
    failing: list[tuple[str, str]] = []
    for item in payload:
        if not isinstance(item, dict):
            raise GitLabProbeError("GitLab pipeline job item was malformed", stale=True)
        status = item.get("status")
        if status not in _FAILING_JOB_STATUSES:
            continue
        name = item.get("name")
        url = item.get("web_url")
        if not isinstance(name, str) or not isinstance(url, str):
            raise GitLabProbeError("GitLab failing pipeline job was malformed", stale=True)
        failing.append((name, url))
    return failing


def _parse_pipeline(item: object) -> GitLabPipeline:
    if not isinstance(item, dict):
        raise GitLabProbeError("GitLab pipeline item was malformed", stale=True)
    pipeline_id = item.get("id")
    status = item.get("status")
    web_url = item.get("web_url")
    if not (isinstance(pipeline_id, int) and isinstance(status, str) and isinstance(web_url, str)):
        raise GitLabProbeError("GitLab pipeline item was malformed", stale=True)
    return GitLabPipeline(id=pipeline_id, status=status, web_url=web_url)


def _stale_pipeline_document(
    request_context: RequestContext, *, repo: str, observed_at: str
) -> CoreContractDocument:
    return unavailable_gates_document(
        request_context,
        repo=repo,
        observed_at=observed_at,
        source_id="gitlab_pipeline_state",
        status="stale",
        safe_user_message=_PIPELINE_STALE_MESSAGE,
    )


def _fetch_merge_request_diffs(
    *,
    repo: str,
    project: str,
    token: str,
    request_branch: str | None,
    merge_requests: list[ForgeReviewPullRequest],
    diff_limit: int,
    opener: HttpOpener,
) -> tuple[list[ForgeReviewPullRequest], list[int], int, int]:
    own_mrs = [mr for mr in merge_requests if _is_own_gitlab_mr(mr, request_branch)]
    other_mrs = [mr for mr in merge_requests if not _is_own_gitlab_mr(mr, request_branch)]
    ordered_for_budget = own_mrs + other_mrs
    to_check = ordered_for_budget[:diff_limit]
    unchecked = ordered_for_budget[diff_limit:]
    unchecked_count = sum(1 for mr in unchecked if not _is_own_gitlab_mr(mr, request_branch))
    updates: dict[int, ForgeReviewPullRequest] = {}
    unbounded_files_mrs: list[int] = []

    for mr in to_check:
        payload, headers = get_json_with_headers(
            f"{gitlab_api_root()}/api/v4/projects/{project}/merge_requests/{mr.number}/diffs"
            "?per_page=100",
            token=token,
            opener=opener,
        )
        paths = _parse_diff_page(payload)
        has_more, _ = _pagination(headers, len(paths), current_page=1)
        if has_more:
            unbounded_files_mrs.append(mr.number)
        updates[mr.number] = replace(mr, changed_paths=tuple(sorted(paths)))

    return (
        [updates.get(mr.number, mr) for mr in merge_requests],
        unbounded_files_mrs,
        len(to_check),
        unchecked_count,
    )


def _is_own_gitlab_mr(mr: ForgeReviewPullRequest, request_branch: str | None) -> bool:
    return (
        request_branch is not None
        and mr.provider == "gitlab"
        and mr.head_ref == request_branch
        and mr.source_project_id is not None
        and mr.source_project_id == mr.target_project_id
    )


def _parse_merge_request_page(*, repo: str, payload: object) -> list[ForgeReviewPullRequest]:
    if not isinstance(payload, list):
        raise GitLabProbeError("GitLab merge-request response was not a list")
    return [_parse_merge_request(repo=repo, item=item) for item in payload]


def _parse_merge_request(*, repo: str, item: object) -> ForgeReviewPullRequest:
    if not isinstance(item, dict):
        raise GitLabProbeError("GitLab merge-request item was malformed")
    number = item.get("iid")
    state = item.get("state")
    url = item.get("web_url")
    created_at = item.get("created_at")
    updated_at = item.get("updated_at")
    source_branch = item.get("source_branch")
    source_project_id = item.get("source_project_id")
    target_project_id = item.get("target_project_id")
    if not (
        isinstance(number, int)
        and isinstance(state, str)
        and isinstance(url, str)
        and isinstance(created_at, str)
        and isinstance(updated_at, str)
        and isinstance(source_branch, str)
        and isinstance(source_project_id, int)
        and isinstance(target_project_id, int)
    ):
        raise GitLabProbeError("GitLab merge-request item was malformed")

    title = item.get("title")
    return ForgeReviewPullRequest(
        provider="gitlab",
        repo=repo,
        number=number,
        state=state,
        url=url,
        title=title if isinstance(title, str) else None,
        changed_paths=(),
        created_at=created_at,
        updated_at=updated_at,
        merged_at=None,
        labels=(),
        head_ref=source_branch,
        head_repo=None,
        source_project_id=source_project_id,
        target_project_id=target_project_id,
    )


def _parse_diff_page(payload: object) -> set[str]:
    if not isinstance(payload, list):
        raise GitLabProbeError("GitLab merge-request diffs response was not a list")
    paths: set[str] = set()
    for item in payload:
        if not isinstance(item, dict):
            raise GitLabProbeError("GitLab merge-request diff item was malformed")
        new_path = item.get("new_path")
        old_path = item.get("old_path")
        if not isinstance(new_path, str):
            raise GitLabProbeError("GitLab merge-request diff item was malformed")
        paths.add(new_path)
        if old_path is not None:
            if not isinstance(old_path, str):
                raise GitLabProbeError("GitLab merge-request diff item was malformed")
            paths.add(old_path)
    return paths


def _pagination(headers: Message, page_size: int, *, current_page: int) -> tuple[bool, int]:
    next_header = headers.get("x-next-page")
    if next_header:
        if not next_header.isdecimal():
            raise GitLabProbeError("GitLab pagination was malformed")
        return True, int(next_header)
    if page_size >= 100:
        return True, current_page + 1
    return False, current_page + 1


def get_json_with_headers(
    url: str, *, token: str, opener: HttpOpener = DEFAULT_OPENER
) -> tuple[object, Message]:
    request = Request(
        url,
        headers={
            "Accept": "application/json",
            "Private-Token": token,
            "User-Agent": "teamctx-gitlab-probe",
        },
    )
    try:
        with opener(request) as response:
            return cast(object, json.loads(response.read().decode("utf-8"))), response.headers
    except HTTPError as exc:
        raise GitLabProbeError("GitLab API request failed", status_code=exc.code) from exc
    except URLError as exc:
        raise GitLabProbeError(f"GitLab API request failed: {exc.reason}") from exc
    except json.JSONDecodeError as exc:
        raise GitLabProbeError("GitLab API response was not valid JSON") from exc


def gitlab_error_message(error: GitLabProbeError, *, source: str) -> str:
    if error.status_code in {401, 404}:
        return f"{source} is unavailable with current access."
    if error.status_code == 403:
        return f"{source} is unavailable or rate-limited with current access."
    if error.status_code == 429:
        return f"{source} is rate-limited."
    return f"{source} is unavailable."
