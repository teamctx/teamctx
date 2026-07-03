from __future__ import annotations

import json
from email.message import Message
from io import BytesIO
from urllib.error import HTTPError
from urllib.request import Request

import pytest

from teamctx.connectors.github import (
    GitHubProbeError,
    fetch_github_pull_requests_graphql,
)

REPO = "acme/widgets"
TOKEN = "tok"
_DEFAULT_HEAD_REPO = object()


class _FakeResponse:
    def __init__(self, payload: object) -> None:
        self._data = json.dumps(payload).encode()

    def read(self) -> bytes:
        return self._data

    def __enter__(self) -> _FakeResponse:
        return self

    def __exit__(self, *_: object) -> None:
        pass


class _GraphQLOpener:
    def __init__(self, *payloads: object) -> None:
        self._payloads = list(payloads)
        self.bodies: list[dict[str, object]] = []

    def __call__(self, request: Request) -> _FakeResponse:
        assert request.full_url == "https://api.github.com/graphql"
        assert request.get_method() == "POST"
        assert request.get_header("Authorization") == f"Bearer {TOKEN}"
        assert request.get_header("Content-type") == "application/json"
        assert request.get_header("X-github-api-version") is None
        body = json.loads((request.data or b"").decode("utf-8"))
        self.bodies.append(body)
        if not self._payloads:
            raise AssertionError("unexpected extra GraphQL request")
        payload = self._payloads.pop(0)
        if isinstance(payload, BaseException):
            raise payload
        return _FakeResponse(payload)


def _node(
    number: int,
    paths: list[str],
    *,
    files_has_next: bool = False,
    title: str = "A title",
    head_repo: object = _DEFAULT_HEAD_REPO,
) -> dict[str, object]:
    head_repository = (
        {"nameWithOwner": REPO} if head_repo is _DEFAULT_HEAD_REPO else head_repo
    )
    return {
        "number": number,
        "url": f"https://github.com/{REPO}/pull/{number}",
        "title": title,
        "createdAt": "2026-07-03T00:00:00Z",
        "updatedAt": "2026-07-03T00:01:00Z",
        "headRefName": "feature/x",
        "headRepository": head_repository,
        "files": {
            "nodes": [{"path": path} for path in paths],
            "pageInfo": {"hasNextPage": files_has_next},
        },
    }


def _page(
    nodes: list[object],
    *,
    has_next: bool = False,
    end_cursor: str | None = None,
) -> dict[str, object]:
    return {
        "data": {
            "repository": {
                "pullRequests": {
                    "nodes": nodes,
                    "pageInfo": {"hasNextPage": has_next, "endCursor": end_cursor},
                }
            }
        }
    }


def test_graphql_repository_null_is_unavailable() -> None:
    opener = _GraphQLOpener({"data": {"repository": None}})

    with pytest.raises(GitHubProbeError):
        fetch_github_pull_requests_graphql(repo=REPO, token=TOKEN, opener=opener)


def test_graphql_data_null_is_unavailable() -> None:
    opener = _GraphQLOpener({"data": None})

    with pytest.raises(GitHubProbeError):
        fetch_github_pull_requests_graphql(repo=REPO, token=TOKEN, opener=opener)


def test_graphql_partial_nodes_with_errors_discards_data() -> None:
    opener = _GraphQLOpener(
        {
            "errors": [{"message": "rate limit", "type": "RATE_LIMITED"}],
            "data": {
                "repository": {
                    "pullRequests": {
                        "nodes": [_node(7, ["src/app.py"])],
                        "pageInfo": {"hasNextPage": False, "endCursor": None},
                    }
                }
            },
        }
    )

    with pytest.raises(GitHubProbeError):
        fetch_github_pull_requests_graphql(repo=REPO, token=TOKEN, opener=opener)


def test_graphql_empty_nodes_with_errors_discards_data() -> None:
    opener = _GraphQLOpener(
        {
            "errors": [{"message": "server error"}],
            "data": {
                "repository": {
                    "pullRequests": {
                        "nodes": [],
                        "pageInfo": {"hasNextPage": False, "endCursor": None},
                    }
                }
            },
        }
    )

    with pytest.raises(GitHubProbeError):
        fetch_github_pull_requests_graphql(repo=REPO, token=TOKEN, opener=opener)


def test_graphql_malformed_node_is_unavailable() -> None:
    opener = _GraphQLOpener(_page([{"number": 7}]))

    with pytest.raises(GitHubProbeError):
        fetch_github_pull_requests_graphql(repo=REPO, token=TOKEN, opener=opener)


def test_graphql_fetches_single_page_shape() -> None:
    opener = _GraphQLOpener(_page([_node(7, ["src/app.py"], title="Touch app")]))

    result = fetch_github_pull_requests_graphql(
        repo=REPO, token=TOKEN, include_titles=True, opener=opener
    )

    assert result.unbounded_list is False
    assert result.unbounded_files_prs == []
    assert len(result.pull_requests) == 1
    pr = result.pull_requests[0]
    assert pr.number == 7
    assert pr.state == "open"
    assert pr.title == "Touch app"
    assert pr.changed_paths == ("src/app.py",)
    assert pr.merged_at is None
    assert pr.labels == ()
    assert pr.head_ref == "feature/x"
    assert pr.head_repo == REPO


def test_graphql_fetches_multiple_pages_with_budget() -> None:
    opener = _GraphQLOpener(
        _page([_node(1, ["src/one.py"])], has_next=True, end_cursor="cursor-1"),
        _page([_node(2, ["src/two.py"])], has_next=False),
    )

    result = fetch_github_pull_requests_graphql(
        repo=REPO, token=TOKEN, max_pages=3, opener=opener
    )

    assert [pr.number for pr in result.pull_requests] == [1, 2]
    assert result.unbounded_list is False
    assert opener.bodies[1]["variables"] == {
        "owner": "acme",
        "name": "widgets",
        "after": "cursor-1",
    }


def test_graphql_exactly_100_without_next_page_is_complete() -> None:
    opener = _GraphQLOpener(_page([_node(i, [f"src/{i}.py"]) for i in range(1, 101)]))

    result = fetch_github_pull_requests_graphql(
        repo=REPO, token=TOKEN, max_pages=1, opener=opener
    )

    assert len(result.pull_requests) == 100
    assert result.unbounded_list is False
    assert result.unbounded_files_prs == []


def test_graphql_page_two_failure_discards_page_one() -> None:
    opener = _GraphQLOpener(
        _page([_node(1, ["src/app.py"])], has_next=True, end_cursor="cursor-1"),
        HTTPError(
            "https://api.github.com/graphql",
            502,
            "Bad Gateway",
            hdrs=Message(),
            fp=BytesIO(b""),
        ),
    )

    with pytest.raises(GitHubProbeError):
        fetch_github_pull_requests_graphql(repo=REPO, token=TOKEN, max_pages=3, opener=opener)


def test_graphql_omits_title_selection_unless_allowed() -> None:
    omitted = _GraphQLOpener(_page([_node(7, ["src/app.py"])]))
    included = _GraphQLOpener(_page([_node(7, ["src/app.py"], title="Touch app")]))

    without_titles = fetch_github_pull_requests_graphql(
        repo=REPO, token=TOKEN, include_titles=False, opener=omitted
    )
    with_titles = fetch_github_pull_requests_graphql(
        repo=REPO, token=TOKEN, include_titles=True, opener=included
    )

    assert "title" not in omitted.bodies[0]["query"]
    assert "title" in included.bodies[0]["query"]
    assert without_titles.pull_requests[0].title is None
    assert with_titles.pull_requests[0].title == "Touch app"


def test_graphql_deleted_fork_null_repo_parses_as_not_own() -> None:
    opener = _GraphQLOpener(_page([_node(7, ["src/app.py"], head_repo=None)]))

    result = fetch_github_pull_requests_graphql(repo=REPO, token=TOKEN, opener=opener)

    assert result.pull_requests[0].head_ref == "feature/x"
    assert result.pull_requests[0].head_repo is None
