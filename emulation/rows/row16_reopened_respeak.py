"""Row 16: Reopened PR re-speaks.

The ambient cache compares the last observed value, not a seen-set. The same PR appears, closes,
and reopens; the second appearance must speak again.
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
    replace_with_clear,
    replace_with_collision,
)
from teamctx.ambient import Delta, FindingMaterial
from teamctx.contract_render import delta_lines

ROW_ID = "16"
TITLE = "Reopened PR re-speaks"


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


def _expected_disappear_line() -> str:
    return delta_lines(
        (
            Delta(
                "disappear",
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
        appeared = run_hook(event, cwd=repo.root, env=env)

        replace_with_clear(fixtures)
        server.reset_graphql()
        backdate_baseline(actor.state_dir, actor.session_id, seconds=120)
        disappeared = run_hook(event, cwd=repo.root, env=env)

        replace_with_collision(fixtures)
        server.reset_graphql()
        backdate_baseline(actor.state_dir, actor.session_id, seconds=120)
        reopened = run_hook(event, cwd=repo.root, env=env)

    appear_line = _expected_appear_line()
    disappear_line = _expected_disappear_line()
    all_delta_context = "\n".join((appeared, disappeared, reopened))
    actual = "\n".join((
        f"first additionalContext: {first}",
        f"appeared additionalContext: {appeared}",
        f"disappeared additionalContext: {disappeared}",
        f"reopened additionalContext: {reopened}",
        f"appear_count: {all_delta_context.count(appear_line)}",
        f"disappear_count: {all_delta_context.count(disappear_line)}",
        f"same_pr_reopened_spoke_again: {str(reopened == appear_line).lower()}",
    ))
    return passed_or_failed(
        ROW_ID,
        TITLE,
        actual,
        Expectation(
            must_match=(
                "appear_count: 2",
                "disappear_count: 1",
                "same_pr_reopened_spoke_again: true",
            ),
            must_absent=("reopened additionalContext: <empty>",),
        ),
        note="last-value re-speak: same PR appears again after closing",
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
