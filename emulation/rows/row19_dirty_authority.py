"""Row 19: Dirty authority is ignored until committed."""

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
from emulation.mockgh import Fixtures, MockGitHub, check_runs_payload, graphql_page
from teamctx.config_failure import CONFIG_DIRTY_NOTE

ROW_ID = "19"
TITLE = "Dirty authority waits for commit"

_PATH = "src/app.py"


def _config() -> str:
    return json.dumps(
        {
            "schema_version": "teamctx.project_config.v0",
            "work_start": {"repo": DEFAULT_SLUG},
        }
    )


def _authority(value: str) -> str:
    return json.dumps(
        [
            {
                "subject": "rounding-cap",
                "source": "confluence:Rounding Policy",
                "priority": 10,
                "value": value,
                "fresh": True,
            }
        ]
    )


def run_offline() -> RowResult:
    with tempfile.TemporaryDirectory() as raw:
        repo = build_lab_repo(Path(raw) / "repo", branch="feature", files={_PATH: "x\n"})
        write_file(repo.root, ".teamctx/config.json", _config())
        write_file(repo.root, ".teamctx/authority.json", _authority("3"))
        commit_files(repo.root, ".teamctx/config.json", ".teamctx/authority.json")
        write_file(repo.root, ".teamctx/authority.json", _authority("99"))
        fixtures = Fixtures(
            graphql_pages=[graphql_page([])], check_runs=check_runs_payload([])
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
                CONFIG_DIRTY_NOTE,
                "Looks clear to start.",
                "Authority",
                "- rounding-cap: resolved (value 3)",
            ),
            must_absent=("- rounding-cap: resolved (value 99)",),
        ),
    )


if __name__ == "__main__":  # pragma: no cover
    result = run_offline()
    print(result.status)
    print(result.actual)
    for outcome in result.outcomes:
        print(outcome.ok, outcome.kind, repr(outcome.subject)[:90])
