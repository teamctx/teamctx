from __future__ import annotations

import json
from email.message import Message
from urllib.request import Request

import pytest

from teamctx.connectors.gitlab import (
    GITLAB_API_ROOT,
    GitLabProbeError,
    fetch_gitlab_merge_requests,
    gitlab_api_root,
)

TOKEN = "tok"
REPO = "group/sub/project"


class _Resp:
    def __init__(self, payload: object, *, headers: dict[str, str] | None = None) -> None:
        self._data = json.dumps(payload).encode()
        self.headers = Message()
        for name, value in (headers or {}).items():
            self.headers[name] = value

    def read(self) -> bytes:
        return self._data

    def __enter__(self) -> _Resp:
        return self

    def __exit__(self, *_: object) -> None:
        pass


class _Opener:
    def __init__(self, *responses: _Resp) -> None:
        self.responses = list(responses)
        self.requests: list[Request] = []

    def __call__(self, request: Request) -> _Resp:
        self.requests.append(request)
        if not self.responses:
            raise AssertionError(f"unexpected request: {request.full_url}")
        return self.responses.pop(0)


def _mr(
    iid: int, *, source_project_id: int = 101, target_project_id: int = 101
) -> dict[str, object]:
    return {
        "iid": iid,
        "state": "opened",
        "web_url": f"https://gitlab.com/{REPO}/-/merge_requests/{iid}",
        "created_at": "2026-07-03T00:00:00Z",
        "updated_at": f"2026-07-03T00:{iid:02d}:00Z",
        "source_branch": "feature/x",
        "source_project_id": source_project_id,
        "target_project_id": target_project_id,
    }


def _diff(path: str) -> dict[str, object]:
    return {"old_path": path, "new_path": path, "renamed_file": False}


def test_default_api_root_is_gitlab() -> None:
    assert GITLAB_API_ROOT == "https://gitlab.com"
    assert gitlab_api_root() == "https://gitlab.com"


def test_gitlab_api_root_env_override(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("TEAMCTX_GITLAB_API_ROOT", "http://127.0.0.1:9999/")

    assert gitlab_api_root() == "http://127.0.0.1:9999"


def test_fetch_encodes_project_slug_and_fetches_diffs() -> None:
    opener = _Opener(
        _Resp([_mr(7)], headers={"x-next-page": ""}),
        _Resp([_diff("src/app.py")], headers={"x-next-page": ""}),
    )

    result = fetch_gitlab_merge_requests(
        repo=REPO,
        token=TOKEN,
        request_branch="feature/x",
        max_pages=3,
        diff_limit=20,
        opener=opener,
    )

    assert [request.full_url for request in opener.requests] == [
        "https://gitlab.com/api/v4/projects/group%2Fsub%2Fproject/merge_requests"
        "?state=opened&order_by=updated_at&sort=desc&per_page=100&page=1",
        "https://gitlab.com/api/v4/projects/group%2Fsub%2Fproject/merge_requests/7/diffs"
        "?per_page=100",
    ]
    assert opener.requests[0].get_header("Private-token") == TOKEN
    assert result.unbounded_list is False
    assert result.diff_checked_count == 1
    assert result.diff_unchecked_count == 0
    assert result.unbounded_files_mrs == []
    mr = result.merge_requests[0]
    assert mr.provider == "gitlab"
    assert mr.number == 7
    assert mr.changed_paths == ("src/app.py",)
    assert mr.head_ref == "feature/x"
    assert mr.source_project_id == 101
    assert mr.target_project_id == 101


def test_fetch_paginates_until_budget_and_marks_unbounded() -> None:
    opener = _Opener(
        _Resp([_mr(1)], headers={"x-next-page": "2"}),
        _Resp([_diff("src/one.py")]),
    )

    result = fetch_gitlab_merge_requests(
        repo=REPO,
        token=TOKEN,
        request_branch=None,
        max_pages=1,
        diff_limit=20,
        opener=opener,
    )

    assert len(opener.requests) == 2
    assert result.unbounded_list is True


def test_fetch_full_page_without_next_header_marks_unbounded() -> None:
    opener = _Opener(_Resp([_mr(i) for i in range(1, 101)], headers={"x-next-page": ""}))

    result = fetch_gitlab_merge_requests(
        repo=REPO,
        token=TOKEN,
        request_branch=None,
        max_pages=1,
        diff_limit=0,
        opener=opener,
    )

    assert result.unbounded_list is True
    assert result.diff_checked_count == 0
    assert result.diff_unchecked_count == 100


def test_diff_budget_counts_non_own_mrs_only_for_unchecked_gap() -> None:
    opener = _Opener(
        _Resp([
            _mr(1),
            _mr(2, source_project_id=202, target_project_id=101),
            _mr(3, source_project_id=303, target_project_id=101),
        ]),
        _Resp([_diff("src/one.py")]),
    )

    result = fetch_gitlab_merge_requests(
        repo=REPO,
        token=TOKEN,
        request_branch="feature/x",
        max_pages=1,
        diff_limit=1,
        opener=opener,
    )

    assert result.diff_checked_count == 1
    assert result.diff_unchecked_count == 2
    assert [mr.number for mr in result.merge_requests] == [1, 2, 3]
    assert result.merge_requests[0].changed_paths == ("src/one.py",)
    assert result.merge_requests[1].changed_paths == ()
    assert result.merge_requests[2].changed_paths == ()


def test_full_diff_page_marks_mr_unbounded() -> None:
    opener = _Opener(
        _Resp([_mr(7)]),
        _Resp([_diff(f"src/{i}.py") for i in range(100)], headers={"x-next-page": ""}),
    )

    result = fetch_gitlab_merge_requests(
        repo=REPO,
        token=TOKEN,
        request_branch=None,
        max_pages=1,
        diff_limit=20,
        opener=opener,
    )

    assert result.unbounded_files_mrs == [7]


@pytest.mark.parametrize(
    "payload",
    [
        {},
        [{"iid": 7}],
        [_mr(7) | {"iid": "7"}],
        [_mr(7) | {"source_project_id": "101"}],
    ],
)
def test_malformed_mr_payload_fails_closed(payload: object) -> None:
    opener = _Opener(_Resp(payload))

    with pytest.raises(GitLabProbeError):
        fetch_gitlab_merge_requests(
            repo=REPO,
            token=TOKEN,
            request_branch=None,
            max_pages=1,
            diff_limit=20,
            opener=opener,
        )


def test_malformed_pagination_fails_closed() -> None:
    opener = _Opener(_Resp([], headers={"x-next-page": "next"}))

    with pytest.raises(GitLabProbeError):
        fetch_gitlab_merge_requests(
            repo=REPO,
            token=TOKEN,
            request_branch=None,
            max_pages=1,
            diff_limit=20,
            opener=opener,
        )


def test_malformed_diff_payload_fails_closed() -> None:
    opener = _Opener(_Resp([_mr(7)]), _Resp([{"new_path": 1}]))

    with pytest.raises(GitLabProbeError):
        fetch_gitlab_merge_requests(
            repo=REPO,
            token=TOKEN,
            request_branch=None,
            max_pages=1,
            diff_limit=20,
            opener=opener,
        )
