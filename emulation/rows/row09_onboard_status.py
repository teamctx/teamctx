"""Row 9: Onboard/status truth.

``teamctx status`` is captured and checked true after every mutation stage: on a bare clone it
reports honestly (no config, hook absent, snippet absent), the reachability line is a live count
never a verdict, ``teamctx onboard`` writes the setup, and a second ``status`` reflects the new
reality (config resolved, hook installed, snippet current). The reachability count is served by the
mock's open-pulls endpoint, so nothing live is touched.
"""

from __future__ import annotations

import tempfile
from pathlib import Path

from emulation.actors import SubprocessEnv, build_lab_repo, run_cli
from emulation.evidence import Expectation, RowResult, combine, passed_or_failed
from emulation.mockgh import Fixtures, MockGitHub

ROW_ID = "09"
TITLE = "Onboard/status truth"

# two open PRs so the reachability line reports an exact count, never a verdict.
_PULLS = Fixtures(pulls=[{"number": 1}, {"number": 2}])


def run_offline() -> RowResult:
    with tempfile.TemporaryDirectory() as raw:
        repo = build_lab_repo(Path(raw) / "repo", branch="feature", files={"src/a.py": "x\n"})
        with MockGitHub(_PULLS) as server:
            env = SubprocessEnv(api_root=server.api_root)
            before = run_cli(["status"], cwd=repo.root, env=env)
            onboard = run_cli(["onboard"], cwd=repo.root, env=env)
            after = run_cli(["status"], cwd=repo.root, env=env)

    before_result = passed_or_failed(
        ROW_ID, TITLE, before.output,
        Expectation(
            must_match=(
                "/.teamctx/config.json; work-start will use the git origin "
                "teamctx-emulation-lab/widgets.",
                "the reflex hook is not installed",
                "no teamctx snippet in CLAUDE.md",
                "reached GitHub: {n} open PRs.",
            ),
            must_absent=("Looks clear to start.",),
        ),
        note="status before onboard",
    )
    onboard_result = passed_or_failed(
        ROW_ID, TITLE, onboard.output,
        Expectation(
            must_match=(
                "[wrote] config:",
                "[wrote] hook:",
                "[wrote] claude_md: added the teamctx snippet to CLAUDE.md.",
                "reached GitHub: {n} open PRs.",
            ),
        ),
        note="onboard",
    )
    after_result = passed_or_failed(
        ROW_ID, TITLE, after.output,
        Expectation(
            must_match=(
                "configures teamctx-emulation-lab/widgets.",
                "the reflex hook is installed",
                "the CLAUDE.md snippet is current.",
                "reached GitHub: {n} open PRs.",
            ),
        ),
        note="status after onboard",
    )
    return combine(ROW_ID, TITLE, [before_result, onboard_result, after_result])


if __name__ == "__main__":  # pragma: no cover
    result = run_offline()
    print(result.status)
    print(result.actual)
    for outcome in result.outcomes:
        print(outcome.ok, outcome.kind, repr(outcome.subject)[:90])
