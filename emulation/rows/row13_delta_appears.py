"""Row 13: The delta appears.

A same-session hook first grounds a clear world. The world then gains an overlapping PR, the
baseline is back-dated past the interval, and the second same-session hook invocation must speak
only the appearance delta. The steady conflict bullet is suppressed: one fact, one voice.
"""

from __future__ import annotations

import tempfile
from pathlib import Path

from emulation.actors import PersistentAmbientActor, run_hook
from emulation.ambient_helpers import backdate_baseline
from emulation.evidence import Expectation, RowResult, passed_or_failed
from emulation.mockgh import MockGitHub
from emulation.rows._ambient_delta import (
    DELTA_FILE,
    DELTA_SESSION,
    build_delta_repo,
    clear_fixtures,
    replace_with_collision,
)
from teamctx.ambient import Delta, FindingMaterial
from teamctx.contract_render import delta_lines

ROW_ID = "13"
TITLE = "Delta appears"


def _expected_appear_line() -> str:
    return delta_lines(
        (
            Delta(
                "appear",
                "conflict",
                FindingMaterial(
                    key="conflict:7",
                    source_display="GitHub PR #7",
                    paths=(DELTA_FILE,),
                ),
            ),
        ),
        (),
        "github",
    )[0]


def _row(tmp: Path) -> RowResult:
    repo = build_delta_repo(tmp / "repo")
    actor = PersistentAmbientActor(state_dir=tmp / "ambient", session_id=DELTA_SESSION)
    fixtures = clear_fixtures()
    with MockGitHub(fixtures) as server:
        env = actor.env(api_root=server.api_root)
        event = actor.pretooluse_event(cwd=repo.root, file_path=DELTA_FILE)
        first = run_hook(event, cwd=repo.root, env=env)

        replace_with_collision(fixtures)
        server.reset_graphql()
        backdate_baseline(actor.state_dir, actor.session_id, seconds=120)
        second = run_hook(event, cwd=repo.root, env=env)

    actual = f"--- first grounding ---\n{first}\n\n--- after PR appears ---\n{second}"
    return passed_or_failed(
        ROW_ID,
        TITLE,
        actual,
        Expectation(
            must_match=(_expected_appear_line(),),
            must_absent=("  • Open PR #7", "teamctx: before you edit"),
        ),
        note="appearance delta; steady bullet suppressed",
    )


def run_offline() -> RowResult:
    with tempfile.TemporaryDirectory() as raw:
        return _row(Path(raw))


if __name__ == "__main__":  # pragma: no cover
    result = run_offline()
    print(result.status)
    print(result.actual)
    for outcome in result.outcomes:
        print(outcome.ok, outcome.kind, repr(outcome.subject)[:90])
