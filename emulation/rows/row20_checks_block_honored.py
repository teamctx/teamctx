"""Row 20: A committed checks block selects the team's enabled checks."""

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
from emulation.evidence import Expectation, RowResult, passed_or_failed
from emulation.mockgh import Fixtures, MockGitHub, check_runs_payload, graphql_page, issue_payload

ROW_ID = "20"
TITLE = "Checks block is honored"

_PATH = "src/app.py"


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


def run_offline() -> RowResult:
    with tempfile.TemporaryDirectory() as raw:
        repo = build_lab_repo(
            Path(raw) / "repo", branch="42-fix-auth", files={_PATH: "x\n"}
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

    return passed_or_failed(
        ROW_ID,
        TITLE,
        run.output,
        Expectation(
            must_match=(
                "Looks clear to start.",
                (
                    "Checked: no other open PRs touch your files; the linked issue's criteria "
                    "are unchanged (issue #42 from your branch name); no failing checks found."
                ),
                "Not enabled by the team: docs (enable in .teamctx/config.json).",
            ),
            must_absent=(
                "the docs you rely on are current",
                "docs/old-auth.md was superseded",
                "Not checked:",
            ),
        ),
    )


if __name__ == "__main__":  # pragma: no cover
    result = run_offline()
    print(result.status)
    print(result.actual)
    for outcome in result.outcomes:
        print(outcome.ok, outcome.kind, repr(outcome.subject)[:90])
