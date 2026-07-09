"""Row 5: Criteria, GitHub, split with the pinned operation ORDER (program spec rev 2, P1-2/P2-3).

(a) An issue is created, Actor B branches ``42-fix-auth`` (which fixes ``since`` at the merge-base),
then Actor C edits the issue AFTER: the criteria check fires with the detail.
(b) The same branch with the issue UNCHANGED since the branch point: the CLEAR line carries
``(issue #42 from your branch name)``, and the ``since`` provenance ``when you branched
(merge-base ...)`` is asserted templated on the resolved inputs (it is structured provenance, not
rendered copy). Issue numbers are templated ``#{n}``; the stable copy spans are byte-exact.
"""

from __future__ import annotations

import tempfile
from pathlib import Path

from emulation.actors import DEFAULT_SLUG, SubprocessEnv, build_lab_repo, run_cli
from emulation.evidence import Expectation, RowResult, combine, passed_or_failed
from emulation.mockgh import Fixtures, MockGitHub, check_runs_payload, graphql_page, issue_payload
from teamctx.resolve import resolve_work_start_inputs

ROW_ID = "05"
TITLE = "Criteria, GitHub"

_BRANCH = "42-fix-auth"
_SINCE = "2026-07-01T09:15:00Z"  # the base-commit (merge-base) date build_lab_repo stamps


def _fixtures(issue_updated_at: str) -> Fixtures:
    return Fixtures(
        graphql_pages=[graphql_page([])],  # no collisions: criteria is the subject
        check_runs=check_runs_payload([]),  # gate clear
        issues={42: issue_payload(42, updated_at=issue_updated_at, slug=DEFAULT_SLUG)},
        issue_events={42: []},
    )


def _changed_sub_row(tmp: Path) -> RowResult:
    repo = build_lab_repo(tmp / "changed", branch=_BRANCH, files={"src/auth.py": "x\n"})
    with MockGitHub(_fixtures(issue_updated_at="2026-07-02T12:00:00Z")) as server:
        env = SubprocessEnv(api_root=server.api_root)
        run = run_cli(["work-start", "--path", "src/auth.py"], cwd=repo.root, env=env)
    expectation = Expectation(
        must_match=(
            "Before you start, here is what to handle first:",
            "Issue #{n} updated: description or comments updated: "
            "re-check the criteria before you rely on them",
        ),
        must_absent=("Looks clear to start.",),
    )
    return passed_or_failed(ROW_ID, TITLE, run.output, expectation, note="criteria changed")


def _unchanged_sub_row(tmp: Path) -> RowResult:
    repo = build_lab_repo(tmp / "unchanged", branch=_BRANCH, files={"src/auth.py": "x\n"})
    with MockGitHub(_fixtures(issue_updated_at="2026-06-30T00:00:00Z")) as server:
        env = SubprocessEnv(api_root=server.api_root)
        run = run_cli(["work-start", "--path", "src/auth.py"], cwd=repo.root, env=env)
    clear = passed_or_failed(
        ROW_ID, TITLE, run.output,
        Expectation(
            must_match=(
                "Looks clear to start.",
                "the linked issue's criteria are unchanged (issue #{n} from your branch name)",
            ),
            must_absent=("Before you start",),
        ),
        note="criteria unchanged (clear line)",
    )
    # The `since` provenance is structured (input_provenance), not rendered copy: assert it on the
    # resolved inputs, templated for the merge-base short sha.
    inputs = resolve_work_start_inputs(paths=("src/auth.py",), token="t", root=repo.root)
    since_provenance = dict(inputs.input_provenance).get("since", "")
    provenance = passed_or_failed(
        ROW_ID, TITLE, since_provenance,
        Expectation(must_match=("when you branched (merge-base {id})",)),
        note="since provenance",
    )
    return combine(ROW_ID, TITLE, [clear, provenance])


def run_offline() -> RowResult:
    with tempfile.TemporaryDirectory() as raw:
        tmp = Path(raw)
        parts = [_changed_sub_row(tmp), _unchanged_sub_row(tmp)]
    return combine(ROW_ID, TITLE, parts)


if __name__ == "__main__":  # pragma: no cover
    result = run_offline()
    print(result.status)
    print(result.actual)
    for outcome in result.outcomes:
        print(outcome.ok, outcome.kind, repr(outcome.subject)[:90])
