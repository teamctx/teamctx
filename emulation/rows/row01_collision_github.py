"""Row 1: Collision, GitHub (plus the own-PR FYI sub-row).

Actor A has an open PR on a different branch touching the file Actor B is about to edit, so
work-start must surface the collision with the PR and the ``gh pr view`` hint, and never read
clear. The own-PR sub-row proves that when the ONLY overlapping open PR is the current branch's
own PR, the conflict check reads clear with an FYI naming the PR (own-detection keys on the PR
HEAD branch vs the request branch, program spec rev 2, P1-1).
"""

from __future__ import annotations

import tempfile
from pathlib import Path

from emulation.actors import DEFAULT_SLUG, SubprocessEnv, build_lab_repo, run_cli
from emulation.evidence import Expectation, RowResult, combine, passed_or_failed
from emulation.mockgh import Fixtures, MockGitHub, check_runs_payload, graphql_page, pr_node

ROW_ID = "01"
TITLE = "Collision, GitHub"

_CLEAR_GATE = check_runs_payload([])  # zero failing check-runs so the gate reads clear, not noise


def _fixtures(head_ref: str) -> Fixtures:
    node = pr_node(7, ["src/a.py"], head_ref=head_ref, head_repo=DEFAULT_SLUG)
    return Fixtures(graphql_pages=[graphql_page([node])], check_runs=_CLEAR_GATE)


def _collision_sub_row(tmp: Path) -> RowResult:
    repo = build_lab_repo(tmp / "collision", branch="feat/x", files={"src/a.py": "x\n"})
    with MockGitHub(_fixtures(head_ref="feat/other")) as server:
        env = SubprocessEnv(api_root=server.api_root)
        run = run_cli(["work-start", "--path", "src/a.py"], cwd=repo.root, env=env)
    expectation = Expectation(
        must_match=(
            "Before you start, here is what to handle first:",
            "Open PR #{n} changed src/a.py: look at it before you edit so you don't undo "
            "each other's work (gh pr view {n} --repo teamctx-emulation-lab/widgets)",
            "Also checked: no failing checks found.",
        ),
        must_absent=("Looks clear to start.",),
    )
    return passed_or_failed(ROW_ID, TITLE, run.output, expectation, note="collision")


def _own_pr_sub_row(tmp: Path) -> RowResult:
    repo = build_lab_repo(tmp / "own", branch="feat/x", files={"src/a.py": "x\n"})
    with MockGitHub(_fixtures(head_ref="feat/x")) as server:
        env = SubprocessEnv(api_root=server.api_root)
        run = run_cli(["work-start", "--path", "src/a.py"], cwd=repo.root, env=env)
    expectation = Expectation(
        must_match=(
            "Looks clear to start.",
            "FYI: Your own open PR #{n} for this branch touches these files; "
            "not flagged as a collision.",
        ),
        must_absent=("Before you start",),
    )
    return passed_or_failed(ROW_ID, TITLE, run.output, expectation, note="own-PR FYI")


def run_offline() -> RowResult:
    with tempfile.TemporaryDirectory() as raw:
        tmp = Path(raw)
        parts = [_collision_sub_row(tmp), _own_pr_sub_row(tmp)]
    return combine(ROW_ID, TITLE, parts)


if __name__ == "__main__":  # pragma: no cover
    result = run_offline()
    print(result.status)
    print(result.actual)
    for outcome in result.outcomes:
        print(outcome.ok, outcome.kind, repr(outcome.subject)[:90])
