"""S1: own-branch PRs are set aside from collisions (spec F1, 2026-07-03)."""

from __future__ import annotations

import json
from urllib.request import Request

from teamctx.connectors.forge_review import (
    ForgeReviewPullRequest,
    normalize_forge_review_prs,
)
from teamctx.connectors.github import parse_github_pull_requests, run_github_pr_probe
from teamctx.contract_render import render_broker_answer
from teamctx.core.broker import broker_answer
from teamctx.core.contracts import RequestContext


def _raw_pr(number: int = 12, head: object = None) -> dict[str, object]:
    pr: dict[str, object] = {
        "number": number,
        "html_url": f"https://github.com/o/r/pull/{number}",
        "state": "open",
        "created_at": "2026-07-01T00:00:00Z",
        "updated_at": "2026-07-02T00:00:00Z",
    }
    if head is not None:
        pr["head"] = head
    return pr


def test_parse_extracts_head_ref_and_head_repo() -> None:
    payload = [_raw_pr(head={"ref": "feat/x", "repo": {"full_name": "o/r"}})]
    prs = parse_github_pull_requests(repo="o/r", pulls_payload=payload, files_by_pr={})
    assert prs[0].head_ref == "feat/x"
    assert prs[0].head_repo == "o/r"


def test_parse_missing_head_yields_none() -> None:
    prs = parse_github_pull_requests(repo="o/r", pulls_payload=[_raw_pr()], files_by_pr={})
    assert prs[0].head_ref is None
    assert prs[0].head_repo is None


def test_parse_deleted_fork_null_repo_yields_none_repo() -> None:
    payload = [_raw_pr(head={"ref": "feat/x", "repo": None})]
    prs = parse_github_pull_requests(repo="o/r", pulls_payload=payload, files_by_pr={})
    assert prs[0].head_ref == "feat/x"
    assert prs[0].head_repo is None


def test_parse_malformed_head_types_yield_none() -> None:
    payload = [_raw_pr(head={"ref": 7, "repo": {"full_name": 3}})]
    prs = parse_github_pull_requests(repo="o/r", pulls_payload=payload, files_by_pr={})
    assert prs[0].head_ref is None
    assert prs[0].head_repo is None


def _request(branch: str | None = "feat/x") -> RequestContext:
    return RequestContext(
        schema_version="teamctx.request_context.v0",
        request_id="t",
        repo="o/r",
        branch=branch,
        task="t",
        paths=["src/a.py"],
        linked_issues=[],
        requested_at="2026-07-03T00:00:00Z",
        requesting_principal=None,
    )


def _pr(number: int, head_ref: str | None, head_repo: str | None) -> ForgeReviewPullRequest:
    return ForgeReviewPullRequest(
        provider="github",
        repo="o/r",
        number=number,
        state="open",
        url=f"https://github.com/o/r/pull/{number}",
        title=None,
        changed_paths=("src/a.py",),
        created_at="2026-07-01T00:00:00Z",
        updated_at="2026-07-02T00:00:00Z",
        head_ref=head_ref,
        head_repo=head_repo,
    )


def test_own_branch_pr_emits_no_collision_and_is_recorded() -> None:
    doc = normalize_forge_review_prs(
        _request(), [_pr(12, "feat/x", "o/r")], observed_at="2026-07-03T00:00:00Z"
    )
    assert doc.source_signals == []
    assert doc.context_cards == []
    assert doc.source_open_targets == []
    status = doc.source_statuses[0]
    assert status.status == "fresh"
    assert status.scope["own_branch_prs"] == ["12"]
    assert "#12" in status.safe_user_message
    assert status.normal_context_visibility == "warning_when_relevant"


def test_other_branch_pr_still_fires() -> None:
    doc = normalize_forge_review_prs(
        _request(), [_pr(13, "feat/other", "o/r")], observed_at="2026-07-03T00:00:00Z"
    )
    assert len(doc.source_signals) == 1
    assert doc.source_statuses[0].normal_context_visibility == "silent"


def test_fork_pr_with_same_branch_name_still_fires() -> None:
    doc = normalize_forge_review_prs(
        _request(), [_pr(14, "feat/x", "someone/fork")], observed_at="2026-07-03T00:00:00Z"
    )
    assert len(doc.source_signals) == 1


def test_unknown_branch_never_matches_own() -> None:
    doc = normalize_forge_review_prs(
        _request(branch=None), [_pr(12, "feat/x", "o/r")], observed_at="2026-07-03T00:00:00Z"
    )
    assert len(doc.source_signals) == 1


def test_missing_head_data_never_matches_own() -> None:
    doc = normalize_forge_review_prs(
        _request(), [_pr(12, None, None)], observed_at="2026-07-03T00:00:00Z"
    )
    assert len(doc.source_signals) == 1


def test_truncated_and_own_pr_keeps_truncation_precedence() -> None:
    doc = normalize_forge_review_prs(
        _request(),
        [_pr(12, "feat/x", "o/r")],
        observed_at="2026-07-03T00:00:00Z",
        coverage_truncated=True,
    )
    status = doc.source_statuses[0]
    assert status.status == "stale"
    assert "most recent 100" in status.safe_user_message
    assert "#12" in status.safe_user_message


class _FakeResponse:
    def __init__(self, payload: object) -> None:
        self._data = json.dumps(payload).encode()

    def read(self) -> bytes:
        return self._data

    def __enter__(self) -> _FakeResponse:
        return self

    def __exit__(self, *_: object) -> None:
        pass


def _own_pr_opener(request: Request) -> _FakeResponse:
    assert request.full_url == "https://api.github.com/graphql"
    return _FakeResponse(
        {
            "data": {
                "repository": {
                    "pullRequests": {
                        "nodes": [
                            {
                                "number": 7,
                                "url": "https://github.com/o/r/pull/7",
                                "createdAt": "2026-07-01T00:00:00Z",
                                "updatedAt": "2026-07-02T00:00:00Z",
                                "headRefName": "feat/x",
                                "headRepository": {"nameWithOwner": "o/r"},
                                "files": {
                                    "nodes": [{"path": "src/a.py"}],
                                    "pageInfo": {"hasNextPage": False},
                                },
                            }
                        ],
                        "pageInfo": {"hasNextPage": False, "endCursor": None},
                    }
                }
            }
        }
    )


def test_end_to_end_own_pr_is_clear_with_fyi() -> None:
    """A repo whose only overlapping open PR is the current branch's own PR must read as a
    clear conflict check (verdict true), with the FYI naming the PR, never a heads-up."""

    request = _request()
    doc = run_github_pr_probe(
        repo="o/r",
        token="tok",
        request_context=request,
        observed_at="2026-07-03T00:00:00Z",
        opener=_own_pr_opener,
    )
    answer = broker_answer(request, doc.source_signals, doc.source_statuses)

    conflict_verdict = dict(answer.verdicts)["Conflict check"]
    output = render_broker_answer(answer)
    assert conflict_verdict.value == "true"
    assert "Looks clear to start." in output
    assert "FYI: Your own open PR #7" in output
    assert "Before you start" not in output


def test_two_own_prs_use_plural_copy() -> None:
    doc = normalize_forge_review_prs(
        _request(),
        [_pr(12, "feat/x", "o/r"), _pr(14, "feat/x", "o/r")],
        observed_at="2026-07-03T00:00:00Z",
    )
    status = doc.source_statuses[0]
    assert status.scope["own_branch_prs"] == ["12", "14"]
    message = status.safe_user_message
    assert "PRs #12, #14" in message
    assert "touch these files" in message
    assert "not flagged as collisions" in message
