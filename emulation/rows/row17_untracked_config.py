"""Row 17: Untracked config is refused.

An uncommitted `.teamctx/config.json` is team semantics that has not gone through the repo's
review path. The normal work-start surface ignores it, runs from the committed/detected defaults,
and says how to activate the team config.
"""

from __future__ import annotations

import json
import tempfile
from pathlib import Path

from emulation.actors import DEFAULT_SLUG, SubprocessEnv, build_lab_repo, run_cli, write_file
from emulation.evidence import Expectation, RowResult, passed_or_failed
from emulation.mockgh import Fixtures, MockGitHub, check_runs_payload, graphql_page, issue_payload
from teamctx.config_failure import COMMIT_CONFIG_TO_ACTIVATE_LINE

ROW_ID = "17"
TITLE = "Untracked config is refused"

_PATH = "src/app.py"


def run_offline() -> RowResult:
    with tempfile.TemporaryDirectory() as raw:
        repo = build_lab_repo(
            Path(raw) / "repo", branch="42-fix-auth", files={_PATH: "x\n"}
        )
        write_file(
            repo.root,
            ".teamctx/config.json",
            json.dumps(
                {
                    "schema_version": "teamctx.project_config.v0",
                    "work_start": {
                        "repo": "some-other-team/widgets",
                        "docs_root": "docs",
                    },
                }
            ),
        )
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
                COMMIT_CONFIG_TO_ACTIVATE_LINE,
                "Looks clear to start.",
                "no other open PRs touch your files",
                "the linked issue's criteria are unchanged (issue #42 from your branch name)",
                "Not checked: docs (no docs root is configured; set work_start.docs_root "
                "to enable).",
            ),
            must_absent=("some-other-team/widgets", "the docs you rely on are current"),
        ),
    )


if __name__ == "__main__":  # pragma: no cover
    result = run_offline()
    print(result.status)
    print(result.actual)
    for outcome in result.outcomes:
        print(outcome.ok, outcome.kind, repr(outcome.subject)[:90])
