"""Narrow GitHub PR metadata probe."""

from __future__ import annotations

import json
from collections.abc import Callable, Mapping
from typing import Protocol, Self, cast
from urllib.error import HTTPError, URLError
from urllib.parse import quote
from urllib.request import Request, urlopen

from teamctx.connectors.forge_review import (
    ForgeReviewPullRequest,
    normalize_forge_review_prs,
    unavailable_forge_review_document,
)
from teamctx.core.contracts import CoreContractDocument, RequestContext

GITHUB_API_ROOT = "https://api.github.com"


class HttpResponse(Protocol):
    def read(self) -> bytes: ...

    def __enter__(self) -> Self: ...

    def __exit__(self, exc_type: object, exc: object, traceback: object) -> object: ...


HttpOpener = Callable[[Request], HttpResponse]
DEFAULT_OPENER = cast(HttpOpener, urlopen)


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
        pull_requests = fetch_github_pull_requests(
            repo=repo, token=token, include_titles=include_titles, opener=opener
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
        pull_requests,
        observed_at=observed_at,
        source_id="github_pr_metadata",
    )


def fetch_github_pull_requests(
    *,
    repo: str,
    token: str,
    include_titles: bool = False,
    opener: HttpOpener = DEFAULT_OPENER,
) -> list[ForgeReviewPullRequest]:
    owner, name = split_repo(repo)
    base = f"{GITHUB_API_ROOT}/repos/{quote(owner)}/{quote(name)}"
    pulls_payload = get_json(f"{base}/pulls?state=open&per_page=30", token=token, opener=opener)
    if not isinstance(pulls_payload, list):
        raise GitHubProbeError("GitHub pulls response was not a list")

    files_by_pr: dict[int, object] = {}
    for raw_pr in pulls_payload:
        if not isinstance(raw_pr, dict):
            continue
        number = raw_pr.get("number")
        if not isinstance(number, int):
            continue
        files_by_pr[number] = get_json(
            f"{base}/pulls/{number}/files?per_page=100",
            token=token,
            opener=opener,
        )

    return parse_github_pull_requests(
        repo=repo,
        pulls_payload=pulls_payload,
        files_by_pr=files_by_pr,
        include_titles=include_titles,
    )


def parse_github_pull_requests(
    *,
    repo: str,
    pulls_payload: object,
    files_by_pr: Mapping[int, object],
    include_titles: bool = False,
) -> list[ForgeReviewPullRequest]:
    if not isinstance(pulls_payload, list):
        raise GitHubProbeError("GitHub pulls response was not a list")

    pull_requests: list[ForgeReviewPullRequest] = []
    for raw_pr in pulls_payload:
        if not isinstance(raw_pr, dict):
            continue
        number = raw_pr.get("number")
        html_url = raw_pr.get("html_url")
        state = raw_pr.get("state")
        created_at = raw_pr.get("created_at")
        updated_at = raw_pr.get("updated_at")
        if not (
            isinstance(number, int)
            and isinstance(html_url, str)
            and isinstance(state, str)
            and isinstance(created_at, str)
            and isinstance(updated_at, str)
        ):
            continue

        files_payload = files_by_pr.get(number, [])
        changed_paths = parse_changed_paths(files_payload)
        labels = parse_label_names(raw_pr.get("labels"))
        title = raw_pr.get("title") if include_titles else None
        pull_requests.append(
            ForgeReviewPullRequest(
                provider="github",
                repo=repo,
                number=number,
                state=state,
                url=html_url,
                title=title if isinstance(title, str) else None,
                changed_paths=tuple(changed_paths),
                created_at=created_at,
                updated_at=updated_at,
                merged_at=(
                    raw_pr.get("merged_at") if isinstance(raw_pr.get("merged_at"), str) else None
                ),
                labels=tuple(labels),
            )
        )
    return pull_requests


def parse_changed_paths(files_payload: object) -> list[str]:
    if not isinstance(files_payload, list):
        return []
    paths: list[str] = []
    for raw_file in files_payload:
        if not isinstance(raw_file, dict):
            continue
        filename = raw_file.get("filename")
        if isinstance(filename, str):
            paths.append(filename)
    return sorted(set(paths))


def parse_label_names(labels_payload: object) -> list[str]:
    if not isinstance(labels_payload, list):
        return []
    labels: list[str] = []
    for raw_label in labels_payload:
        if not isinstance(raw_label, dict):
            continue
        name = raw_label.get("name")
        if isinstance(name, str):
            labels.append(name)
    return sorted(set(labels))


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
