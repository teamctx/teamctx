"""Tests for GitHub truncation honesty: no false clear when PR list or file list is full.

When the PR list comes back full (>= 100) or any PR's file list comes back full (>= 100),
we cannot know whether a collision exists past what we fetched, so the forge-review source
status becomes stale, which routes to incomplete[stale-dep], which makes the conflict
verdict UNKNOWN (not clear). A visible collision in the fetched page still fires.
"""

from __future__ import annotations

import json
from typing import Any
from urllib.request import Request

from teamctx.connectors.github import (
    ForgeReviewFetch,
    fetch_github_pull_requests,
    run_github_pr_probe,
)
from teamctx.core.broker import broker_answer
from teamctx.core.contracts import RequestContext
from teamctx.core.evaluate import Valuation
from teamctx.core.select import derive_cards

OBS = "2026-06-28T00:00:00Z"
REPO = "acme/widgets"
TOKEN = "tok"


def _request(paths: list[str] = ("src/x.py",)) -> RequestContext:
    return RequestContext(
        schema_version="teamctx.request_context.v0",
        request_id="req-trunc",
        repo=REPO,
        branch="feature/x",
        task="edit x",
        paths=list(paths),
        linked_issues=[],
        requested_at=OBS,
        requesting_principal=None,
    )


def _raw_pr(number: int) -> dict[str, Any]:
    """A minimal syntactically-valid GitHub PR payload."""
    return {
        "number": number,
        "html_url": f"https://github.com/{REPO}/pull/{number}",
        "state": "open",
        "created_at": "2026-06-28T00:00:00Z",
        "updated_at": "2026-06-28T00:01:00Z",
        "labels": [],
    }


def _fake_file(filename: str) -> dict[str, str]:
    return {"filename": filename, "status": "modified"}


class _FakeResponse:
    def __init__(self, payload: object) -> None:
        self._data = json.dumps(payload).encode()

    def read(self) -> bytes:
        return self._data

    def __enter__(self) -> _FakeResponse:
        return self

    def __exit__(self, *_: object) -> None:
        pass


def _make_opener(
    *,
    num_prs: int,
    colliding_pr_number: int | None = None,
    colliding_path: str = "src/x.py",
    files_per_pr: int = 1,
) -> Any:
    """Build an opener that returns `num_prs` PRs. If `colliding_pr_number` is given, PR
    with that number has `colliding_path` in its file list. All other PRs get an unrelated
    file. `files_per_pr` controls how many files to return for each PR's file call."""

    pulls = [_raw_pr(i) for i in range(1, num_prs + 1)]

    def opener(request: Request) -> _FakeResponse:
        url = request.full_url
        # PR list endpoint
        if url.endswith("/pulls?state=open&per_page=100"):
            return _FakeResponse(pulls)
        # per-PR files endpoint
        for pr in pulls:
            number = pr["number"]
            if f"/pulls/{number}/files?per_page=100" in url:
                if colliding_pr_number is not None and number == colliding_pr_number:
                    files = [_fake_file(colliding_path)]
                    # pad to the requested count
                    while len(files) < files_per_pr:
                        files.append(_fake_file(f"other/file_{len(files)}.py"))
                else:
                    files = [_fake_file(f"unrelated/file_{number}.py")]
                    while len(files) < files_per_pr:
                        files.append(_fake_file(f"unrelated/more_{len(files)}.py"))
                return _FakeResponse(files)
        raise AssertionError(f"unexpected URL in test opener: {url}")

    return opener


# ---------------------------------------------------------------------------
# Test 1: truncated PR list, no collision -> forge-review status stale -> UNKNOWN verdict
# ---------------------------------------------------------------------------


def test_truncated_pr_list_no_collision_gives_stale_status_and_unknown_verdict() -> None:
    """100 PRs returned (a full page implies more exist); none touch src/x.py.
    The source status must be stale and the conflict verdict must be UNKNOWN."""

    opener = _make_opener(num_prs=100)
    request = _request()

    document = run_github_pr_probe(
        repo=REPO,
        token=TOKEN,
        request_context=request,
        observed_at=OBS,
        opener=opener,
    )

    # Source status must be non-fresh (stale) because the list was truncated
    assert document.source_statuses[0].status == "stale", (
        f"expected stale, got {document.source_statuses[0].status!r}"
    )
    # No collision card (nothing overlaps in the fetched page)
    assert derive_cards(document.request_context, document.source_signals) == []
    assert document.context_cards == []

    # End-to-end: the conflict verdict through the real broker is UNKNOWN, not clear
    answer = broker_answer(request, document.source_signals, document.source_statuses)
    conflict_verdict = dict(answer.verdicts)["Conflict check"]
    assert conflict_verdict == Valuation("unknown", "incomplete[stale-dep]"), (
        f"expected UNKNOWN, got {conflict_verdict!r}"
    )


# ---------------------------------------------------------------------------
# Test 2: truncated list WITH a visible collision -> collision card still fires
# ---------------------------------------------------------------------------


def test_truncated_pr_list_with_visible_collision_still_emits_collision_card() -> None:
    """100 PRs returned (truncated). PR #3 touches src/x.py.
    The collision card must still be present even under truncation."""

    opener = _make_opener(num_prs=100, colliding_pr_number=3, colliding_path="src/x.py")
    request = _request()

    document = run_github_pr_probe(
        repo=REPO,
        token=TOKEN,
        request_context=request,
        observed_at=OBS,
        opener=opener,
    )

    # Status is stale (truncated)
    assert document.source_statuses[0].status == "stale"
    # Collision card for PR #3 must be present
    cards = derive_cards(document.request_context, document.source_signals)
    assert len(cards) == 1
    assert "PR #3" in cards[0].text
    assert "src/x.py" in cards[0].text
    assert cards[0].source_body == "status_only"
    assert cards[0].reason_code == "collision.same_path"
    assert cards[0].source_open_target_id is None
    assert document.source_open_targets[0].id == "open_github_pr_3"

    # End-to-end: a visible collision falsifies the conflict universal even under
    # truncation. The verdict is FALSE (collision found), not UNKNOWN.
    answer = broker_answer(request, document.source_signals, document.source_statuses)
    conflict_verdict = dict(answer.verdicts)["Conflict check"]
    assert conflict_verdict == Valuation("false"), (
        f"expected FALSE (collision found), got {conflict_verdict!r}"
    )


# ---------------------------------------------------------------------------
# Test 3: not truncated (< 100 PRs, no collision) -> status fresh -> clear
# ---------------------------------------------------------------------------


def test_small_pr_list_no_collision_gives_fresh_status() -> None:
    """2 PRs returned (well under 100). No collision -> status must be fresh."""

    opener = _make_opener(num_prs=2)
    request = _request()

    document = run_github_pr_probe(
        repo=REPO,
        token=TOKEN,
        request_context=request,
        observed_at=OBS,
        opener=opener,
    )

    assert document.source_statuses[0].status == "fresh"
    assert derive_cards(document.request_context, document.source_signals) == []
    assert document.context_cards == []


# ---------------------------------------------------------------------------
# Test 4: single PR with a full (100) file list -> truncated=True
# ---------------------------------------------------------------------------


def test_full_files_page_marks_truncated() -> None:
    """A single PR whose file list comes back with 100 entries signals that more files
    exist; fetch_github_pull_requests must return truncated=True."""

    opener = _make_opener(num_prs=1, files_per_pr=100)

    result = fetch_github_pull_requests(
        repo=REPO,
        token=TOKEN,
        opener=opener,
    )

    assert isinstance(result, ForgeReviewFetch)
    assert result.truncated is True


# ---------------------------------------------------------------------------
# Test 5: fetch_github_pull_requests returns ForgeReviewFetch with correct fields
# ---------------------------------------------------------------------------


def test_fetch_github_pull_requests_returns_forge_review_fetch_not_truncated() -> None:
    """2 PRs, 1 file each -> ForgeReviewFetch.truncated is False."""

    opener = _make_opener(num_prs=2)

    result = fetch_github_pull_requests(
        repo=REPO,
        token=TOKEN,
        opener=opener,
    )

    assert isinstance(result, ForgeReviewFetch)
    assert result.truncated is False
    assert len(result.pull_requests) == 2
