"""Row 21: A disabled check is visible without running or silently disappearing."""

from __future__ import annotations

import json
import tempfile
from pathlib import Path

from emulation.actors import (
    DEFAULT_SLUG,
    SYNTHETIC_TOKEN,
    SubprocessEnv,
    build_lab_repo,
    commit_files,
    process_env,
    run_cli,
    write_file,
)
from emulation.evidence import Expectation, RowResult, passed_or_failed
from emulation.mockgh import Fixtures, MockGitHub, check_runs_payload, graphql_page, issue_payload
from teamctx.resolve import resolve_work_start_inputs
from teamctx.work_start import work_start_answer

ROW_ID = "21"
TITLE = "Disabled check is visible"

_PATH = "src/app.py"
_SUPERSEDED_DOC = "---\nsuperseded_by: docs/new-auth.md\n---\nOld auth design.\n"


def _config() -> str:
    return json.dumps(
        {
            "schema_version": "teamctx.project_config.v0",
            "work_start": {"repo": DEFAULT_SLUG, "docs_root": "docs"},
            "checks": {
                "conflict": {"enabled": True},
                "criteria": {"enabled": True},
                "docs": {"enabled": False},
                "gate": {"enabled": True},
            },
        }
    )


def _closure_evidence(repo_root: Path, api_root: str) -> str:
    with process_env(
        TEAMCTX_GITHUB_API_ROOT=api_root,
        TEAMCTX_DISABLE_GH_AUTH="1",
        GITHUB_TOKEN=SYNTHETIC_TOKEN,
        GITHUB_TOKEN_FILE=None,
        ATLASSIAN_EMAIL=None,
        ATLASSIAN_API_TOKEN=None,
        ATLASSIAN_API_TOKEN_FILE=None,
    ):
        inputs = resolve_work_start_inputs(
            paths=(_PATH,),
            token=SYNTHETIC_TOKEN,
            root=repo_root,
        )
        answer = work_start_answer(
            inputs, observed_at="2026-07-08T00:00:00Z", project_root=repo_root
        )
    closure = {entry.check_id: entry.closure_status for entry in answer.selection.closure}
    return "\n".join(f"{check}: {status}" for check, status in sorted(closure.items()))


def run_offline() -> RowResult:
    with tempfile.TemporaryDirectory() as raw:
        repo = build_lab_repo(
            Path(raw) / "repo",
            branch="42-fix-auth",
            files={
                _PATH: "x\n",
                "docs/old-auth.md": _SUPERSEDED_DOC,
                "docs/new-auth.md": "# New auth design\n",
            },
        )
        write_file(repo.root, ".teamctx/config.json", _config())
        commit_files(repo.root, ".teamctx/config.json")
        fixtures = Fixtures(
            graphql_pages=[graphql_page([])],
            check_runs=check_runs_payload([]),
            issues={
                42: issue_payload(
                    42,
                    updated_at="2026-06-30T00:00:00Z",
                    slug=DEFAULT_SLUG,
                )
            },
            issue_events={42: []},
        )
        with MockGitHub(fixtures) as gh:
            run = run_cli(
                ["work-start", "--path", _PATH],
                cwd=repo.root,
                env=SubprocessEnv(api_root=gh.api_root),
            )
            closure = _closure_evidence(repo.root, gh.api_root)

    actual = run.output + "\nClosure\n" + closure + "\n"
    return passed_or_failed(
        ROW_ID,
        TITLE,
        actual,
        Expectation(
            must_match=(
                "Not enabled by the team: docs (enable in .teamctx/config.json).",
                "docs: disabled-by-team",
            ),
            must_absent=(
                "docs/old-auth.md was superseded",
                "the docs you rely on are current",
                "Not checked: docs",
                "Couldn't check: docs",
            ),
        ),
    )


if __name__ == "__main__":  # pragma: no cover
    result = run_offline()
    print(result.status)
    print(result.actual)
    for outcome in result.outcomes:
        print(outcome.ok, outcome.kind, repr(outcome.subject)[:90])
