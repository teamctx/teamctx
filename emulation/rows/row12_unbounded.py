"""Row 12: Unbounded at scale (program spec rev 2, P0-1).

A fabricated 301+-PR payload is driven through the REAL pipeline via the ``TEAMCTX_GITHUB_API_ROOT``
seam: the full CLI fetches its whole page budget (300 PRs), none touching the file, and the last
page still has more, so the conflict check reports the coverage as incomplete with n=300 and NEVER
reads clear. The reflex hook, on the same busy repo, surfaces the same honest partial-check note
(its own reflex page budget), never a false all-clear. Evidence is tagged test-verified
(fabricated payload, real pipeline).
"""

from __future__ import annotations

import tempfile
from pathlib import Path

from emulation.actors import (
    SubprocessEnv,
    build_lab_repo,
    pretooluse_event,
    run_cli,
    run_hook,
)
from emulation.evidence import Expectation, RowResult, combine, passed_or_failed
from emulation.mockgh import Fixtures, MockGitHub, check_runs_payload, graphql_page, pr_node

ROW_ID = "12"
TITLE = "Unbounded at scale"

EVIDENCE_TAG = "test-verified (fabricated payload, real pipeline)"

_PER_PAGE = 100
_PAGES = 3  # the full-profile page budget: 3 x 100 = 300 fetched, and more still exist


def _fixtures() -> Fixtures:
    pages = []
    for page in range(_PAGES):
        nodes = [
            pr_node(
                page * _PER_PAGE + i,
                ["docs/unrelated.md"],  # none touch src/a.py: no collision, only unboundedness
                head_ref=f"feat/pr-{page * _PER_PAGE + i}",
                head_repo="teamctx-emulation-lab/widgets",
            )
            for i in range(1, _PER_PAGE + 1)
        ]
        pages.append(graphql_page(nodes, has_next=True, end_cursor=f"cursor-{page}"))
    return Fixtures(graphql_pages=pages, check_runs=check_runs_payload([]))


def _cli_sub_row(tmp: Path) -> RowResult:
    repo = build_lab_repo(tmp / "cli", branch="feature", files={"src/a.py": "x\n"})
    with MockGitHub(_fixtures()) as server:
        env = SubprocessEnv(api_root=server.api_root)
        run = run_cli(["work-start", "--path", "src/a.py"], cwd=repo.root, env=env)
    expectation = Expectation(
        must_match=(
            "Heads up: I can't confirm the important things yet:",
            "Checked the {n} most recently updated open PRs; more exist, so this is not a "
            "complete check.",
        ),
        must_absent=("Looks clear to start.", "no other open PRs touch your files"),
    )
    return passed_or_failed(ROW_ID, TITLE, run.output, expectation, note="full CLI (n=300)")


def _hook_sub_row(tmp: Path) -> RowResult:
    repo = build_lab_repo(tmp / "hook", branch="feature", files={"src/a.py": "x\n"})
    with MockGitHub(_fixtures()) as server:
        env = SubprocessEnv(api_root=server.api_root, ambient_state=tmp / "ambient")
        event = pretooluse_event(cwd=repo.root, file_path="src/a.py")
        context = run_hook(event, cwd=repo.root, env=env)
    expectation = Expectation(
        must_match=(
            "teamctx checked the {n} most recently updated open PRs and found no collision, "
            "but more open PRs exist. On a repo this busy, glance at GitHub if this file is "
            "sensitive.",
        ),
        must_absent=("looks clear to start",),
    )
    return passed_or_failed(ROW_ID, TITLE, context, expectation, note="reflex hook")


def run_offline() -> RowResult:
    with tempfile.TemporaryDirectory() as raw:
        tmp = Path(raw)
        parts = [_cli_sub_row(tmp), _hook_sub_row(tmp)]
    result = combine(ROW_ID, TITLE, parts)
    return RowResult(
        row_id=result.row_id,
        title=result.title,
        status=result.status,
        outcomes=result.outcomes,
        actual=result.actual,
        note=EVIDENCE_TAG,
    )


if __name__ == "__main__":  # pragma: no cover
    result = run_offline()
    print(result.status, "|", result.note)
    print(result.actual)
    for outcome in result.outcomes:
        print(outcome.ok, outcome.kind, repr(outcome.subject)[:90])
