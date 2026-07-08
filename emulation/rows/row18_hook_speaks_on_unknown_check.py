"""Row 18: The hook speaks when the committed team config names an unknown check."""

from __future__ import annotations

import json
import tempfile
from pathlib import Path

from emulation.actors import (
    DEFAULT_SLUG,
    SubprocessEnv,
    build_lab_repo,
    commit_files,
    pretooluse_event,
    run_hook,
    write_file,
)
from emulation.evidence import Expectation, RowResult, passed_or_failed
from emulation.mockgh import Fixtures, MockGitHub, check_runs_payload, graphql_page
from teamctx.config_failure import TEAM_CONFIG_UPGRADE_LINE

ROW_ID = "18"
TITLE = "Hook speaks on unknown check"

_PATH = "src/app.py"


def run_offline() -> RowResult:
    with tempfile.TemporaryDirectory() as raw:
        repo = build_lab_repo(Path(raw) / "repo", branch="feature", files={_PATH: "x\n"})
        write_file(
            repo.root,
            ".teamctx/config.json",
            json.dumps(
                {
                    "schema_version": "teamctx.project_config.v0",
                    "work_start": {"repo": DEFAULT_SLUG},
                    "checks": {"x_future": {"enabled": True}},
                }
            ),
        )
        commit_files(repo.root, ".teamctx/config.json")
        fixtures = Fixtures(
            graphql_pages=[graphql_page([])], check_runs=check_runs_payload([])
        )
        with MockGitHub(fixtures) as gh:
            context = run_hook(
                pretooluse_event(cwd=repo.root, file_path=_PATH),
                cwd=repo.root,
                env=SubprocessEnv(api_root=gh.api_root),
            )

    return passed_or_failed(
        ROW_ID,
        TITLE,
        context,
        Expectation(
            must_match=(TEAM_CONFIG_UPGRADE_LINE,),
            must_absent=("Looks clear to start.", "no other open PRs touch your files"),
        ),
    )


if __name__ == "__main__":  # pragma: no cover
    result = run_offline()
    print(result.status)
    print(result.actual)
    for outcome in result.outcomes:
        print(outcome.ok, outcome.kind, repr(outcome.subject)[:90])
