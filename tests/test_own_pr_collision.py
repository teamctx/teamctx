"""S1: own-branch PRs are set aside from collisions (spec F1, 2026-07-03)."""

from __future__ import annotations

from teamctx.connectors.github import parse_github_pull_requests


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
