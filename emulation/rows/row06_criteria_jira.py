"""Row 6: Criteria, Jira, through the real Jira connector and renderer.

(a) Actor B branches ``PROJ-123-fix`` (fixing ``since`` at the merge-base), then Actor C edits the
Jira description AFTER: work-start fires with field-level detail and ``why`` shows the Jira source
display.
(b) The same derived Jira key with NO Jira config reports the pinned disabled note and never the
criteria-clear line.
(c) A mixed issue family (GitHub ``#42`` fresh/unchanged, Jira ``PROJ-123`` unconfigured) reads as
couldn't-check, never as "the linked issue's criteria are unchanged".
"""

from __future__ import annotations

import json
import tempfile
from pathlib import Path

from emulation.actors import (
    DEFAULT_SLUG,
    SubprocessEnv,
    build_lab_repo,
    commit_files,
    run_cli,
    write_file,
)
from emulation.evidence import Expectation, RowResult, combine, passed_or_failed
from emulation.mockgh import Fixtures, MockGitHub, check_runs_payload, graphql_page, issue_payload
from emulation.mockjira import (
    JiraFixtures,
    MockJira,
    changelog_history,
    changelog_payload,
)
from emulation.mockjira import (
    issue_payload as jira_issue_payload,
)

ROW_ID = "06"
TITLE = "Criteria, Jira"

_JIRA_BRANCH = "PROJ-123-fix"
_MIXED_BRANCH = "42-PROJ-123-fix"
_PATH = "src/app.py"


def _github_clear(
    *,
    issues: dict[int, dict[str, object]] | None = None,
    issue_events: dict[int, list[dict[str, object]]] | None = None,
) -> Fixtures:
    return Fixtures(
        graphql_pages=[graphql_page([])],
        check_runs=check_runs_payload([]),
        issues=issues or {},
        issue_events=issue_events or {},
    )


def _write_config(repo_root: Path, *, jira_base_url: str | None = None) -> None:
    work_start: dict[str, object] = {"repo": DEFAULT_SLUG}
    if jira_base_url is not None:
        work_start["jira"] = {"base_url": jira_base_url}
    write_file(
        repo_root,
        ".teamctx/config.json",
        json.dumps({"schema_version": "teamctx.project_config.v0", "work_start": work_start}),
    )
    commit_files(repo_root, ".teamctx/config.json")


def _jira_changed_sub_row(tmp: Path) -> RowResult:
    repo = build_lab_repo(tmp / "jira-changed", branch=_JIRA_BRANCH, files={_PATH: "x\n"})
    jira_fixtures = JiraFixtures(
        issues={
            "PROJ-123": jira_issue_payload(
                "PROJ-123",
                updated_at="2026-07-02T12:00:00.000+0000",
                summary="Acceptance criteria",
            )
        },
        changelogs={
            "PROJ-123": changelog_payload(
                [
                    changelog_history(
                        "2026-07-02T11:00:00.000+0000", ("description",)
                    )
                ],
                is_last=True,
            )
        },
    )
    with MockGitHub(_github_clear()) as gh, MockJira(jira_fixtures) as jira:
        _write_config(repo.root, jira_base_url=jira.base_url)
        env = SubprocessEnv(
            api_root=gh.api_root,
            atlassian_email="operator@emulation.example",
            atlassian_api_token="synthetic-atlassian-token",
        )
        work_start = run_cli(["work-start", "--path", _PATH], cwd=repo.root, env=env)
        why = run_cli(["why", "issue:PROJ-123", "--path", _PATH], cwd=repo.root, env=env)

    actual = f"--- work-start ---\n{work_start.output}\n--- why ---\n{why.output}"
    return passed_or_failed(
        ROW_ID,
        TITLE,
        actual,
        Expectation(
            must_match=(
                "Before you start, here is what to handle first:",
                "Jira PROJ-123 updated: description updated: "
                "re-check the criteria before you rely on them",
                "Source: Jira PROJ-123: Acceptance criteria (fresh, high confidence).",
            ),
            must_absent=("the linked issue's criteria are unchanged",),
        ),
        note="jira description changed",
    )


def _unconfigured_jira_sub_row(tmp: Path) -> RowResult:
    repo = build_lab_repo(tmp / "jira-unconfigured", branch=_JIRA_BRANCH, files={_PATH: "x\n"})
    _write_config(repo.root)
    with MockGitHub(_github_clear()) as gh:
        run = run_cli(
            ["work-start", "--path", _PATH],
            cwd=repo.root,
            env=SubprocessEnv(api_root=gh.api_root),
        )
    return passed_or_failed(
        ROW_ID,
        TITLE,
        run.output,
        Expectation(
            must_match=(
                "issue PROJ-123 looks like a Jira issue, but no Jira is configured; "
                "add work_start.jira to .teamctx/config.json",
            ),
            must_absent=("the linked issue's criteria are unchanged",),
        ),
        note="jira key without config",
    )


def _mixed_family_sub_row(tmp: Path) -> RowResult:
    repo = build_lab_repo(tmp / "mixed-family", branch=_MIXED_BRANCH, files={_PATH: "x\n"})
    _write_config(repo.root)
    gh_fixtures = _github_clear(
        issues={
            42: issue_payload(
                42,
                updated_at="2026-06-30T00:00:00Z",
                slug=DEFAULT_SLUG,
            )
        },
        issue_events={42: []},
    )
    with MockGitHub(gh_fixtures) as gh:
        run = run_cli(
            ["work-start", "--path", _PATH],
            cwd=repo.root,
            env=SubprocessEnv(api_root=gh.api_root),
        )
    return passed_or_failed(
        ROW_ID,
        TITLE,
        run.output,
        Expectation(
            must_match=("Couldn't check: spec changes (couldn't reach GitHub).",),
            must_absent=("the linked issue's criteria are unchanged",),
        ),
        note="mixed GitHub fresh plus Jira unconfigured",
    )


def run_offline() -> RowResult:
    with tempfile.TemporaryDirectory() as raw:
        tmp = Path(raw)
        parts = [
            _jira_changed_sub_row(tmp),
            _unconfigured_jira_sub_row(tmp),
            _mixed_family_sub_row(tmp),
        ]
    return combine(ROW_ID, TITLE, parts)


if __name__ == "__main__":  # pragma: no cover
    result = run_offline()
    print(result.status)
    print(result.actual)
    for outcome in result.outcomes:
        print(outcome.ok, outcome.kind, repr(outcome.subject)[:90])
