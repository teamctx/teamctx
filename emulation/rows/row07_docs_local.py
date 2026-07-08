"""Row 7: Docs, local (declared supersession).

A locally-declared superseded doc must fire a heads-up naming the replacement; a clean configured
docs tree must read CLEAR ("the docs you rely on are current"), and ``not_applicable`` must appear
NOWHERE (program spec rev 2, P2-4). GitHub is served empty through the mock so the conflict and
gate checks read clear and the docs verdict is the row's subject.
"""

from __future__ import annotations

import json
import tempfile
from pathlib import Path

from emulation.actors import SubprocessEnv, build_lab_repo, commit_files, run_cli, write_file
from emulation.evidence import Expectation, RowResult, combine, passed_or_failed
from emulation.mockgh import Fixtures, MockGitHub, check_runs_payload, graphql_page

ROW_ID = "07"
TITLE = "Docs, local"

_EMPTY_GITHUB = Fixtures(graphql_pages=[graphql_page([])], check_runs=check_runs_payload([]))

_SUPERSEDED_DOC = "---\nsuperseded_by: docs/new-auth.md\n---\nOld auth design.\n"
_CURRENT_DOC = "# Auth design\nStill current.\n"


def _commit_team_config(root: Path) -> None:
    write_file(
        root,
        ".teamctx/config.json",
        json.dumps(
            {
                "schema_version": "teamctx.project_config.v0",
                "work_start": {"repo": "teamctx-emulation-lab/widgets", "docs_root": "docs"},
            }
        ),
    )
    commit_files(root, ".teamctx/config.json")


def _superseded_sub_row(tmp: Path) -> RowResult:
    repo = build_lab_repo(
        tmp / "superseded",
        branch="feature",
        files={
            "src/a.py": "x\n",
            "docs/old-auth.md": _SUPERSEDED_DOC,
            "docs/new-auth.md": "# New auth design\n",
        },
    )
    _commit_team_config(repo.root)
    with MockGitHub(_EMPTY_GITHUB) as server:
        env = SubprocessEnv(api_root=server.api_root)
        run = run_cli(["work-start", "--path", "src/a.py"], cwd=repo.root, env=env)
    expectation = Expectation(
        must_match=(
            "Before you start, here is what to handle first:",
            "docs/old-auth.md was superseded by docs/new-auth.md: rely on the current one instead",
        ),
        must_absent=("Looks clear to start.", "not_applicable", "not applicable"),
    )
    return passed_or_failed(ROW_ID, TITLE, run.output, expectation, note="superseded")


def _clean_sub_row(tmp: Path) -> RowResult:
    repo = build_lab_repo(
        tmp / "clean",
        branch="feature",
        files={"src/a.py": "x\n", "docs/auth.md": _CURRENT_DOC},
    )
    _commit_team_config(repo.root)
    with MockGitHub(_EMPTY_GITHUB) as server:
        env = SubprocessEnv(api_root=server.api_root)
        run = run_cli(["work-start", "--path", "src/a.py"], cwd=repo.root, env=env)
    expectation = Expectation(
        must_match=(
            "Looks clear to start.",
            "the docs you rely on are current",
        ),
        must_absent=("not_applicable", "not applicable", "Before you start"),
    )
    return passed_or_failed(ROW_ID, TITLE, run.output, expectation, note="clean docs")


def run_offline() -> RowResult:
    with tempfile.TemporaryDirectory() as raw:
        tmp = Path(raw)
        parts = [_superseded_sub_row(tmp), _clean_sub_row(tmp)]
    return combine(ROW_ID, TITLE, parts)


if __name__ == "__main__":  # pragma: no cover
    result = run_offline()
    print(result.status)
    print(result.actual)
    for outcome in result.outcomes:
        print(outcome.ok, outcome.kind, repr(outcome.subject)[:90])
