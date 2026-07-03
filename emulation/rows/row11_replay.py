"""Row 11: Replay (program spec rev 2, P1-5).

The same composed conflict scenario is replayed with the IDENTICAL ``observed_at`` against the same
captured payloads (served offline through the mock via the seam), and the two runs must produce an
identical digest and identical output. Live sources are never assumed frozen: determinism is proven
against the pinned payloads, not against a live repo.

Mechanism (recorded per the plan): ``observed_at`` is injected as a PARAMETER to
``render_work_start`` (``work_start`` invocation), never a CLI flag and never a new env read, so no
production code path is altered. The mock's GraphQL page cursor is rewound between runs so the
second run re-serves byte-identical pages.
"""

from __future__ import annotations

import hashlib
import tempfile
from pathlib import Path

from emulation.actors import SYNTHETIC_TOKEN, process_env
from emulation.evidence import Expectation, RowResult, evaluate
from emulation.mockgh import MockGitHub
from emulation.rows._shared import CONFLICT_FILE, build_conflict_repo, conflict_fixtures
from teamctx.resolve import resolve_work_start_inputs
from teamctx.work_start import render_work_start

ROW_ID = "11"
TITLE = "Replay"

_OBSERVED_AT = "2026-07-03T12:00:00Z"  # the pinned instant, identical across both replay runs


def _render(clone: Path, api_root: str) -> str:
    with process_env(
        TEAMCTX_GITHUB_API_ROOT=api_root,
        TEAMCTX_DISABLE_GH_AUTH="1",
        GITHUB_TOKEN=SYNTHETIC_TOKEN,
        GITHUB_TOKEN_FILE=None,
    ):
        inputs = resolve_work_start_inputs(
            paths=(CONFLICT_FILE,), token=SYNTHETIC_TOKEN, root=clone
        )
        return render_work_start(inputs, observed_at=_OBSERVED_AT, project_root=clone)


def run_offline() -> RowResult:
    with tempfile.TemporaryDirectory() as raw:
        clone = build_conflict_repo(Path(raw) / "repo").root
        with MockGitHub(conflict_fixtures()) as server:
            first = _render(clone, server.api_root)
            server.reset_graphql()  # rewind the page cursor so the replay re-serves the same pages
            second = _render(clone, server.api_root)

    digest_first = hashlib.sha256(first.encode("utf-8")).hexdigest()
    digest_second = hashlib.sha256(second.encode("utf-8")).hexdigest()
    marker = "\n".join(
        [
            "OUTPUT-IDENTICAL" if first == second else "OUTPUT-DIFFERENT",
            "DIGEST-IDENTICAL" if digest_first == digest_second else "DIGEST-DIFFERENT",
            "SCENARIO-NONTRIVIAL" if "PR #7" in first else "SCENARIO-EMPTY",
        ]
    )
    expectation = Expectation(
        must_match=("OUTPUT-IDENTICAL", "DIGEST-IDENTICAL", "SCENARIO-NONTRIVIAL"),
        must_absent=("OUTPUT-DIFFERENT", "DIGEST-DIFFERENT"),
    )
    status, outcomes = evaluate(marker, expectation)
    evidence = f"observed_at={_OBSERVED_AT}\ndigest={digest_first}\n\n{first}"
    return RowResult(ROW_ID, TITLE, status, outcomes, actual=evidence)


if __name__ == "__main__":  # pragma: no cover
    result = run_offline()
    print(result.status)
    print(result.actual)
    for outcome in result.outcomes:
        print(outcome.ok, outcome.kind, repr(outcome.subject)[:90])
