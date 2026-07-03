"""Unit tests for the emulation actor + mock-transport scaffolding.

The mock is exercised THROUGH the real teamctx connectors over the ``TEAMCTX_GITHUB_API_ROOT``
seam, so what these tests assert is exactly what the offline rows will drive.
"""

from __future__ import annotations

from pathlib import Path

import pytest

from emulation import mockgh, mockgl
from emulation.actors import (
    build_lab_repo,
    fresh_session_id,
    pretooluse_event,
)
from emulation.mockgh import Fixtures, MockGitHub
from emulation.mockgl import GitLabFixtures, MockGitLab
from teamctx.connectors.github import fetch_github_pull_requests
from teamctx.connectors.github_checks import fetch_failing_check_runs
from teamctx.connectors.github_issues import fetch_issue_changes
from teamctx.connectors.gitlab import (
    fetch_gitlab_failing_pipeline_jobs,
    fetch_gitlab_merge_requests,
    fetch_latest_gitlab_pipeline,
)
from teamctx.discover import derive_since
from teamctx.git_context import detect_branch, detect_forge_repo, detect_repo

SLUG = "teamctx-emulation-lab/widgets"


# --- actors: tmp-repo builder ---


def test_build_lab_repo_is_auto_detectable(tmp_path: Path) -> None:
    repo = build_lab_repo(tmp_path, branch="feat/core", files={"src/a.py": "x\n"})
    assert detect_repo(repo.root) == SLUG
    assert detect_branch(repo.root) == "feat/core"


def test_build_lab_repo_issue_branch_derives_since(tmp_path: Path) -> None:
    build_lab_repo(tmp_path, branch="42-fix-auth", files={"src/auth.py": "x\n"})
    derived = derive_since(tmp_path)
    assert derived is not None
    _timestamp, provenance = derived
    assert "when you branched (merge-base" in provenance


def test_build_lab_repo_dates_the_base_commit(tmp_path: Path) -> None:
    build_lab_repo(tmp_path, branch="feature", files={"src/a.py": "x\n"})
    derived = derive_since(tmp_path)
    assert derived is not None
    assert derived[0] == "2026-07-01T09:15:00Z"  # the base-commit date, normalized to UTC


# --- actors: synthetic PreToolUse event ---


def test_pretooluse_event_has_exactly_the_hook_fields(tmp_path: Path) -> None:
    event = pretooluse_event(cwd=tmp_path, file_path="src/a.py", session_id="s1")
    assert event["hook_event_name"] == "PreToolUse"
    assert event["tool_name"] == "Edit"
    assert event["tool_input"] == {"file_path": "src/a.py"}
    assert event["cwd"] == str(tmp_path)
    assert event["session_id"] == "s1"


def test_fresh_session_id_is_unique() -> None:
    assert fresh_session_id() != fresh_session_id()


# --- mockgh: through the real connectors ---


def test_mock_graphql_serves_pr_pages(monkeypatch: pytest.MonkeyPatch) -> None:
    node = mockgh.pr_node(7, ["src/a.py"], head_ref="feat/other", head_repo=SLUG)
    fixtures = Fixtures(graphql_pages=[mockgh.graphql_page([node])])
    with MockGitHub(fixtures) as server:
        monkeypatch.setenv("TEAMCTX_GITHUB_API_ROOT", server.api_root)
        fetch = fetch_github_pull_requests(repo=SLUG, token="t")
    assert [pr.number for pr in fetch.pull_requests] == [7]
    assert fetch.pull_requests[0].changed_paths == ("src/a.py",)
    assert fetch.unbounded_list is False


def test_mock_graphql_paging_marks_unbounded(monkeypatch: pytest.MonkeyPatch) -> None:
    # three full pages, the last still hasNextPage -> the unbounded (row 12) shape.
    pages = [
        mockgh.graphql_page(
            [mockgh.pr_node(i, ["docs/x.md"], head_ref="feat/x", head_repo=SLUG)],
            has_next=True,
            end_cursor=f"cursor-{page}",
        )
        for page, i in enumerate((1, 2, 3), start=1)
    ]
    fixtures = Fixtures(graphql_pages=pages)
    with MockGitHub(fixtures) as server:
        monkeypatch.setenv("TEAMCTX_GITHUB_API_ROOT", server.api_root)
        fetch = fetch_github_pull_requests(repo=SLUG, token="t", max_pages=3)
    assert fetch.unbounded_list is True
    assert [pr.number for pr in fetch.pull_requests] == [1, 2, 3]


def test_mock_check_runs_serves_failing(monkeypatch: pytest.MonkeyPatch) -> None:
    payload = mockgh.check_runs_payload([mockgh.check_run("build", "failure")])
    with MockGitHub(Fixtures(check_runs=payload)) as server:
        monkeypatch.setenv("TEAMCTX_GITHUB_API_ROOT", server.api_root)
        fetch = fetch_failing_check_runs(repo=SLUG, ref="feature", token="t")
    assert [name for name, _url in fetch.failing] == ["build"]
    assert fetch.pending is False


def test_mock_check_runs_serves_pending(monkeypatch: pytest.MonkeyPatch) -> None:
    payload = mockgh.check_runs_payload([mockgh.check_run("slow", None, status="in_progress")])
    with MockGitHub(Fixtures(check_runs=payload)) as server:
        monkeypatch.setenv("TEAMCTX_GITHUB_API_ROOT", server.api_root)
        fetch = fetch_failing_check_runs(repo=SLUG, ref="feature", token="t")
    assert fetch.failing == []
    assert fetch.pending is True


def test_mock_issues_serves_a_change(monkeypatch: pytest.MonkeyPatch) -> None:
    fixtures = Fixtures(
        issues={42: mockgh.issue_payload(42, updated_at="2026-07-02T00:00:00Z")},
        issue_events={42: []},
    )
    with MockGitHub(fixtures) as server:
        monkeypatch.setenv("TEAMCTX_GITHUB_API_ROOT", server.api_root)
        changes = fetch_issue_changes(
            repo=SLUG, issues=["#42"], since="2026-07-01T00:00:00Z", token="t"
        )
    assert [change.issue for change in changes] == ["#42"]


def test_mock_issues_unchanged_before_since_yields_no_change(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    fixtures = Fixtures(
        issues={42: mockgh.issue_payload(42, updated_at="2026-06-30T00:00:00Z")},
        issue_events={42: []},
    )
    with MockGitHub(fixtures) as server:
        monkeypatch.setenv("TEAMCTX_GITHUB_API_ROOT", server.api_root)
        changes = fetch_issue_changes(
            repo=SLUG, issues=["#42"], since="2026-07-01T00:00:00Z", token="t"
        )
    assert changes == []


# --- actors: gitlab-origin tmp repo ---


def test_build_lab_repo_gitlab_origin_detects_gitlab(tmp_path: Path) -> None:
    repo = build_lab_repo(
        tmp_path, branch="feat/x", files={"src/a.py": "x\n"}, origin_host="gitlab.com"
    )
    assert detect_forge_repo(repo.root) == (SLUG, "gitlab")
    assert detect_branch(repo.root) == "feat/x"


# --- mockgl: through the real GitLab connectors ---


def test_mock_serves_mr_list_and_diffs(monkeypatch: pytest.MonkeyPatch) -> None:
    fixtures = GitLabFixtures(
        mr_pages=[[mockgl.mr_item(5, source_branch="feat/other")]],
        mr_diffs={5: [mockgl.diff_item("src/a.py")]},
    )
    with MockGitLab(fixtures) as server:
        monkeypatch.setenv("TEAMCTX_GITLAB_API_ROOT", server.api_root)
        fetch = fetch_gitlab_merge_requests(repo=SLUG, token="t", request_branch="feat/x")
    assert [mr.number for mr in fetch.merge_requests] == [5]
    assert fetch.merge_requests[0].changed_paths == ("src/a.py",)
    assert fetch.unbounded_list is False


def test_mock_mr_paging_marks_unbounded(monkeypatch: pytest.MonkeyPatch) -> None:
    # two pages; page 1 carries x-next-page, so a one-page budget reports the list as unbounded.
    fixtures = GitLabFixtures(
        mr_pages=[
            [mockgl.mr_item(1, source_branch="feat/a")],
            [mockgl.mr_item(2, source_branch="feat/b")],
        ],
        mr_diffs={1: [mockgl.diff_item("docs/x.md")]},
    )
    with MockGitLab(fixtures) as server:
        monkeypatch.setenv("TEAMCTX_GITLAB_API_ROOT", server.api_root)
        fetch = fetch_gitlab_merge_requests(
            repo=SLUG, token="t", request_branch="feat/x", max_pages=1
        )
    assert fetch.unbounded_list is True
    assert [mr.number for mr in fetch.merge_requests] == [1]


def test_mock_serves_latest_pipeline(monkeypatch: pytest.MonkeyPatch) -> None:
    fixtures = GitLabFixtures(pipelines=[mockgl.pipeline_item(10, "failed")])
    with MockGitLab(fixtures) as server:
        monkeypatch.setenv("TEAMCTX_GITLAB_API_ROOT", server.api_root)
        pipeline = fetch_latest_gitlab_pipeline(repo=SLUG, ref="feat/x", token="t")
    assert pipeline is not None
    assert (pipeline.id, pipeline.status) == (10, "failed")


def test_mock_zero_pipelines_returns_none(monkeypatch: pytest.MonkeyPatch) -> None:
    with MockGitLab(GitLabFixtures(pipelines=[])) as server:
        monkeypatch.setenv("TEAMCTX_GITLAB_API_ROOT", server.api_root)
        pipeline = fetch_latest_gitlab_pipeline(repo=SLUG, ref="feat/x", token="t")
    assert pipeline is None


def test_mock_serves_failing_jobs(monkeypatch: pytest.MonkeyPatch) -> None:
    fixtures = GitLabFixtures(
        pipelines=[mockgl.pipeline_item(10, "failed")],
        pipeline_jobs={10: [mockgl.job_item("test", "failed"), mockgl.job_item("lint", "success")]},
    )
    with MockGitLab(fixtures) as server:
        monkeypatch.setenv("TEAMCTX_GITLAB_API_ROOT", server.api_root)
        pipeline = fetch_latest_gitlab_pipeline(repo=SLUG, ref="feat/x", token="t")
        assert pipeline is not None
        jobs = fetch_gitlab_failing_pipeline_jobs(repo=SLUG, pipeline=pipeline, token="t")
    assert [name for name, _url in jobs] == ["test"]
