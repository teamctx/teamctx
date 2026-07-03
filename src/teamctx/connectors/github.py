"""Narrow GitHub PR metadata probe."""

from __future__ import annotations

import json
from collections.abc import Callable, Mapping
from dataclasses import dataclass, field
from typing import Protocol, Self, TypedDict, cast
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen

from teamctx.connectors.forge_review import (
    ForgeReviewPullRequest,
    normalize_forge_review_prs,
    unavailable_forge_review_document,
)
from teamctx.core.contracts import CoreContractDocument, RequestContext

GITHUB_API_ROOT = "https://api.github.com"


def github_api_root() -> str:
    """The GitHub API root, env-overridable via ``TEAMCTX_GITHUB_API_ROOT`` (trailing slash
    stripped). The override exists for the emulation program: fabricated payloads can be driven
    through the REAL pipeline against a local mock server. Read at call time, never cached.
    Token-sensitive: requests to the override host carry the resolved token; this is an
    intentional local-operator seam for tests and validation harnesses only."""

    import os

    return os.environ.get("TEAMCTX_GITHUB_API_ROOT", GITHUB_API_ROOT).rstrip("/")


class HttpResponse(Protocol):
    def read(self) -> bytes: ...

    def __enter__(self) -> Self: ...

    def __exit__(self, exc_type: object, exc: object, traceback: object) -> object: ...


HttpOpener = Callable[[Request], HttpResponse]
DEFAULT_OPENER = cast(HttpOpener, urlopen)


class _PullRequestConnection(TypedDict):
    nodes: list[object]
    page_info: dict[str, object]


@dataclass(frozen=True)
class ForgeReviewFetch:
    """Result of fetching open PRs from the GitHub API.

    ``pull_requests`` is the list of PRs parsed from the response.
    ``unbounded_list`` is True when more open PRs exist past the configured page budget.
    ``unbounded_files_prs`` names PRs whose file list continues past the first 100 files.
    Both cases mean the coverage is incomplete and the conflict check cannot assert a clean
    all-clear.
    """

    pull_requests: list[ForgeReviewPullRequest]
    unbounded_list: bool = False
    unbounded_files_prs: list[int] = field(default_factory=list)


class GitHubProbeError(RuntimeError):
    def __init__(self, message: str, *, status_code: int | None = None) -> None:
        super().__init__(message)
        self.status_code = status_code


def run_github_pr_probe(
    *,
    repo: str,
    token: str | None,
    request_context: RequestContext,
    observed_at: str,
    include_titles: bool = False,
    max_pages: int = 3,
    opener: HttpOpener = DEFAULT_OPENER,
) -> CoreContractDocument:
    if not token:
        return unavailable_forge_review_document(
            request_context,
            provider="github",
            repo=repo,
            observed_at=observed_at,
            safe_user_message="GitHub PR metadata is unavailable because no token is configured.",
        )

    try:
        fetch = fetch_github_pull_requests(
            repo=repo,
            token=token,
            include_titles=include_titles,
            max_pages=max_pages,
            opener=opener,
        )
    except GitHubProbeError as exc:
        return unavailable_forge_review_document(
            request_context,
            provider="github",
            repo=repo,
            observed_at=observed_at,
            safe_user_message=github_error_message(exc),
        )

    return normalize_forge_review_prs(
        request_context,
        fetch.pull_requests,
        observed_at=observed_at,
        source_id="github_pr_metadata",
        coverage_unbounded_list=fetch.unbounded_list,
        unbounded_files_prs=fetch.unbounded_files_prs,
    )


def fetch_github_pull_requests(
    *,
    repo: str,
    token: str,
    include_titles: bool = False,
    max_pages: int = 3,
    opener: HttpOpener = DEFAULT_OPENER,
) -> ForgeReviewFetch:
    return fetch_github_pull_requests_graphql(
        repo=repo,
        token=token,
        include_titles=include_titles,
        max_pages=max_pages,
        opener=opener,
    )


def fetch_github_pull_requests_graphql(
    *,
    repo: str,
    token: str,
    include_titles: bool = False,
    max_pages: int = 3,
    opener: HttpOpener = DEFAULT_OPENER,
) -> ForgeReviewFetch:
    owner, name = split_repo(repo)
    after: str | None = None
    pull_requests: list[ForgeReviewPullRequest] = []
    unbounded_files_prs: list[int] = []
    query = _pull_requests_graphql_query(include_titles=include_titles)

    if max_pages < 1:
        raise GitHubProbeError("GitHub GraphQL page budget must be at least one")

    for page_number in range(1, max_pages + 1):
        payload = graphql_json(
            query,
            {"owner": owner, "name": name, "after": after},
            token=token,
            opener=opener,
        )
        connection = _pull_request_connection(payload)
        nodes = connection["nodes"]
        page_info = connection["page_info"]
        page_prs, file_overflow_prs = _parse_graphql_pull_request_nodes(
            repo=repo,
            nodes=nodes,
            include_titles=include_titles,
        )
        pull_requests.extend(page_prs)
        unbounded_files_prs.extend(file_overflow_prs)

        has_next_page = page_info.get("hasNextPage")
        if not isinstance(has_next_page, bool):
            raise GitHubProbeError("GitHub GraphQL pageInfo was malformed")
        if not has_next_page:
            return ForgeReviewFetch(
                pull_requests=pull_requests,
                unbounded_list=False,
                unbounded_files_prs=unbounded_files_prs,
            )
        if page_number == max_pages:
            return ForgeReviewFetch(
                pull_requests=pull_requests,
                unbounded_list=True,
                unbounded_files_prs=unbounded_files_prs,
            )
        end_cursor = page_info.get("endCursor")
        if not isinstance(end_cursor, str) or not end_cursor:
            raise GitHubProbeError("GitHub GraphQL pageInfo was malformed")
        after = end_cursor

    raise GitHubProbeError("GitHub GraphQL page budget was invalid")


def _pull_requests_graphql_query(*, include_titles: bool) -> str:
    title_field = "title" if include_titles else ""
    return f"""
query TeamctxPullRequests($owner: String!, $name: String!, $after: String) {{
  repository(owner: $owner, name: $name) {{
    pullRequests(
      states: OPEN
      first: 100
      after: $after
      orderBy: {{field: UPDATED_AT, direction: DESC}}
    ) {{
      nodes {{
        number
        url
        {title_field}
        createdAt
        updatedAt
        headRefName
        headRepository {{
          nameWithOwner
        }}
        files(first: 100) {{
          nodes {{
            path
          }}
          pageInfo {{
            hasNextPage
          }}
        }}
      }}
      pageInfo {{
        hasNextPage
        endCursor
      }}
    }}
  }}
}}
"""


def _pull_request_connection(payload: object) -> _PullRequestConnection:
    if not isinstance(payload, dict):
        raise GitHubProbeError("GitHub GraphQL response was not an object")
    errors = payload.get("errors")
    if isinstance(errors, list) and errors:
        if all(isinstance(error, dict) and error.get("type") == "RATE_LIMITED"
               for error in errors):
            raise GitHubProbeError("GitHub GraphQL response was rate-limited", status_code=429)
        raise GitHubProbeError("GitHub GraphQL response contained errors")
    data = payload.get("data")
    if not isinstance(data, dict):
        raise GitHubProbeError("GitHub GraphQL response was missing data")
    repository = data.get("repository")
    if not isinstance(repository, dict):
        raise GitHubProbeError("GitHub GraphQL repository was unavailable")
    pull_requests = repository.get("pullRequests")
    if not isinstance(pull_requests, dict):
        raise GitHubProbeError("GitHub GraphQL pullRequests was malformed")
    nodes = pull_requests.get("nodes")
    if not isinstance(nodes, list):
        raise GitHubProbeError("GitHub GraphQL pullRequests nodes was malformed")
    page_info = pull_requests.get("pageInfo")
    if not isinstance(page_info, dict):
        raise GitHubProbeError("GitHub GraphQL pageInfo was malformed")
    return {"nodes": nodes, "page_info": page_info}


def _parse_graphql_pull_request_nodes(
    *,
    repo: str,
    nodes: list[object],
    include_titles: bool,
) -> tuple[list[ForgeReviewPullRequest], list[int]]:
    pull_requests: list[ForgeReviewPullRequest] = []
    unbounded_files_prs: list[int] = []
    for node in nodes:
        pr, files_have_next = _parse_graphql_pull_request_node(
            repo=repo,
            node=node,
            include_titles=include_titles,
        )
        pull_requests.append(pr)
        if files_have_next:
            unbounded_files_prs.append(pr.number)
    return pull_requests, unbounded_files_prs


def _parse_graphql_pull_request_node(
    *,
    repo: str,
    node: object,
    include_titles: bool,
) -> tuple[ForgeReviewPullRequest, bool]:
    if not isinstance(node, dict):
        raise GitHubProbeError("GitHub GraphQL pull request node was malformed")
    number = node.get("number")
    url = node.get("url")
    created_at = node.get("createdAt")
    updated_at = node.get("updatedAt")
    files = node.get("files")
    if not (
        isinstance(number, int)
        and isinstance(url, str)
        and isinstance(created_at, str)
        and isinstance(updated_at, str)
        and isinstance(files, dict)
    ):
        raise GitHubProbeError("GitHub GraphQL pull request node was malformed")

    file_nodes = files.get("nodes")
    file_page_info = files.get("pageInfo")
    if not isinstance(file_nodes, list) or not isinstance(file_page_info, dict):
        raise GitHubProbeError("GitHub GraphQL pull request files were malformed")
    files_have_next = file_page_info.get("hasNextPage")
    if not isinstance(files_have_next, bool):
        raise GitHubProbeError("GitHub GraphQL pull request files were malformed")

    changed_paths: list[str] = []
    for file_node in file_nodes:
        if not isinstance(file_node, dict):
            raise GitHubProbeError("GitHub GraphQL pull request file was malformed")
        path = file_node.get("path")
        if not isinstance(path, str):
            raise GitHubProbeError("GitHub GraphQL pull request file was malformed")
        changed_paths.append(path)

    title = node.get("title") if include_titles else None
    head_ref = node.get("headRefName")
    head_repository = node.get("headRepository")
    head_repo: str | None = None
    if isinstance(head_repository, dict):
        name_with_owner = head_repository.get("nameWithOwner")
        head_repo = name_with_owner if isinstance(name_with_owner, str) else None

    return (
        ForgeReviewPullRequest(
            provider="github",
            repo=repo,
            number=number,
            state="open",
            url=url,
            title=title if isinstance(title, str) else None,
            changed_paths=tuple(sorted(set(changed_paths))),
            created_at=created_at,
            updated_at=updated_at,
            merged_at=None,
            labels=(),
            head_ref=head_ref if isinstance(head_ref, str) else None,
            head_repo=head_repo,
        ),
        files_have_next,
    )


def get_json(url: str, *, token: str, opener: HttpOpener = DEFAULT_OPENER) -> object:
    request = Request(
        url,
        headers={
            "Accept": "application/vnd.github+json",
            "Authorization": f"Bearer {token}",
            "User-Agent": "teamctx-github-pr-probe",
            "X-GitHub-Api-Version": "2022-11-28",
        },
    )
    try:
        with opener(request) as response:
            return cast(object, json.loads(response.read().decode("utf-8")))
    except HTTPError as exc:
        raise GitHubProbeError("GitHub API request failed", status_code=exc.code) from exc
    except URLError as exc:
        raise GitHubProbeError(f"GitHub API request failed: {exc.reason}") from exc
    except json.JSONDecodeError as exc:
        raise GitHubProbeError("GitHub API response was not valid JSON") from exc


def graphql_json(
    query: str,
    variables: Mapping[str, object],
    *,
    token: str,
    opener: HttpOpener = DEFAULT_OPENER,
) -> object:
    request = Request(
        f"{github_api_root()}/graphql",
        data=json.dumps({"query": query, "variables": dict(variables)}).encode("utf-8"),
        headers={
            "Authorization": f"Bearer {token}",
            "Content-Type": "application/json",
            "User-Agent": "teamctx-github-pr-probe",
        },
    )
    try:
        with opener(request) as response:
            return cast(object, json.loads(response.read().decode("utf-8")))
    except HTTPError as exc:
        raise GitHubProbeError("GitHub API request failed", status_code=exc.code) from exc
    except URLError as exc:
        raise GitHubProbeError(f"GitHub API request failed: {exc.reason}") from exc
    except json.JSONDecodeError as exc:
        raise GitHubProbeError("GitHub API response was not valid JSON") from exc


def github_error_message(error: GitHubProbeError) -> str:
    if error.status_code in {401, 404}:
        return "GitHub PR metadata is unavailable with current access."
    if error.status_code == 403:
        return "GitHub PR metadata is unavailable or rate-limited with current access."
    if error.status_code == 429:
        return "GitHub PR metadata is rate-limited."
    return "GitHub PR metadata is unavailable."


def split_repo(repo: str) -> tuple[str, str]:
    parts = repo.split("/", 1)
    if len(parts) != 2 or not parts[0] or not parts[1]:
        raise GitHubProbeError("GitHub repo must be in owner/name form")
    return parts[0], parts[1]
