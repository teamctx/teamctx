"""Row 3: Gate, GitHub, all four sub-cases (program spec rev 2, including P1-8).

(a) A failing check fires a heads-up. (b) A slow (still-running) job reads live pending, never a
false green. (c) With the token removed, GitHub is unreachable and the row reads can't-verify,
never clear. (d) Zero check-runs reads CLEAR, affirmatively recorded as the documented
GitHub/GitLab asymmetry (GitHub has no gate configured => nothing failing => clear; the GitLab
half, that zero-pipelines reads a disabled note, is row 4).
"""

from __future__ import annotations

import tempfile
from pathlib import Path

from emulation.actors import SubprocessEnv, build_lab_repo, run_cli
from emulation.evidence import Expectation, RowResult, combine, passed_or_failed
from emulation.mockgh import (
    Fixtures,
    MockGitHub,
    check_run,
    check_runs_payload,
    graphql_page,
)

ROW_ID = "03"
TITLE = "Gate, GitHub"

_NO_COLLISION = [graphql_page([])]


def _gate_fixtures(runs: list[dict[str, object]]) -> Fixtures:
    return Fixtures(graphql_pages=_NO_COLLISION, check_runs=check_runs_payload(runs))


def _failing_sub_row(tmp: Path) -> RowResult:
    repo = build_lab_repo(tmp / "failing", branch="feature", files={"src/a.py": "x\n"})
    fixtures = _gate_fixtures([check_run("build", "failure")])
    with MockGitHub(fixtures) as server:
        env = SubprocessEnv(api_root=server.api_root)
        run = run_cli(["work-start", "--path", "src/a.py"], cwd=repo.root, env=env)
    expectation = Expectation(
        must_match=(
            "Before you start, here is what to handle first:",
            "Check 'build' is failing on this branch: fix it or wait for a green build "
            "before relying on it",
        ),
        must_absent=("Looks clear to start.",),
    )
    return passed_or_failed(ROW_ID, TITLE, run.output, expectation, note="failing check")


def _pending_sub_row(tmp: Path) -> RowResult:
    repo = build_lab_repo(tmp / "pending", branch="feature", files={"src/a.py": "x\n"})
    fixtures = _gate_fixtures([check_run("slow", None, status="in_progress")])
    with MockGitHub(fixtures) as server:
        env = SubprocessEnv(api_root=server.api_root)
        run = run_cli(["work-start", "--path", "src/a.py"], cwd=repo.root, env=env)
    expectation = Expectation(
        must_match=(
            "Heads up: I can't confirm the important things yet:",
            "CI checks are still running, so the gate isn't confirmed green yet.",
        ),
        must_absent=("no failing checks found", "Looks clear to start."),
    )
    return passed_or_failed(ROW_ID, TITLE, run.output, expectation, note="pending (slow job)")


def _token_removed_sub_row(tmp: Path) -> RowResult:
    repo = build_lab_repo(tmp / "notoken", branch="feature", files={"src/a.py": "x\n"})
    fixtures = _gate_fixtures([check_run("build", "failure")])
    with MockGitHub(fixtures) as server:
        env = SubprocessEnv(api_root=server.api_root, token="")  # credential removed
        run = run_cli(["work-start", "--path", "src/a.py"], cwd=repo.root, env=env)
    expectation = Expectation(
        must_match=(
            "Heads up: I can't confirm the important things yet:",
            "teamctx couldn't reach GitHub.",
            "GITHUB_TOKEN",
        ),
        must_absent=("Looks clear to start.", "no failing checks found"),
    )
    return passed_or_failed(ROW_ID, TITLE, run.output, expectation, note="token removed")


def _zero_checks_sub_row(tmp: Path) -> RowResult:
    repo = build_lab_repo(tmp / "zero", branch="feature", files={"src/a.py": "x\n"})
    fixtures = _gate_fixtures([])  # zero check-runs: the GitHub asymmetry reads CLEAR
    with MockGitHub(fixtures) as server:
        env = SubprocessEnv(api_root=server.api_root)
        run = run_cli(["work-start", "--path", "src/a.py"], cwd=repo.root, env=env)
    expectation = Expectation(
        must_match=(
            "Looks clear to start.",
            "no failing checks found",
        ),
        must_absent=("Before you start", "couldn't reach GitHub", "still running"),
    )
    return passed_or_failed(ROW_ID, TITLE, run.output, expectation, note="zero check-runs (clear)")


def run_offline() -> RowResult:
    with tempfile.TemporaryDirectory() as raw:
        tmp = Path(raw)
        parts = [
            _failing_sub_row(tmp),
            _pending_sub_row(tmp),
            _token_removed_sub_row(tmp),
            _zero_checks_sub_row(tmp),
        ]
    return combine(ROW_ID, TITLE, parts)


if __name__ == "__main__":  # pragma: no cover
    result = run_offline()
    print(result.status)
    print(result.actual)
    for outcome in result.outcomes:
        print(outcome.ok, outcome.kind, repr(outcome.subject)[:90])
