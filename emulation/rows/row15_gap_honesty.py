"""Row 15: Gap honesty.

A good baseline may not hide a new unverified source gap. The row grounds a clear world, makes the
mock GitHub source unreachable, and proves the gap is spoken immediately. It then back-dates the
persisting gap past the restatement floor and proves the same gap is spoken again after a real
re-check, never silently served over an unspoken gap.
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
    only_baseline,
    replace_with_unreachable,
)
from teamctx.ambient import Delta, FindingMaterial
from teamctx.contract_render import delta_lines

ROW_ID = "15"
TITLE = "Gap honesty"


def _expected_gap_line() -> str:
    return delta_lines(
        (
            Delta(
                "coverage_shrank",
                "conflict",
                FindingMaterial(key="conflict:__source__"),
                note="couldn't reach GitHub",
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

        replace_with_unreachable(fixtures)
        server.reset_graphql()
        backdate_baseline(actor.state_dir, actor.session_id, seconds=120)
        gap = run_hook(event, cwd=repo.root, env=env)
        after_gap = only_baseline(actor.state_dir, actor.session_id)

        backdate_baseline(actor.state_dir, actor.session_id, seconds=901)
        before_restatement = only_baseline(actor.state_dir, actor.session_id)
        restatement = run_hook(event, cwd=repo.root, env=env)
        after_restatement = only_baseline(actor.state_dir, actor.session_id)

    gap_context_spoken = bool(gap.strip())
    restatement_context_spoken = bool(restatement.strip())
    network_advanced = (
        float(after_restatement["last_network_check_at"])
        > float(before_restatement["last_network_check_at"])
    )
    spoken_advanced = (
        float(after_restatement["last_spoken_at"]) > float(before_restatement["last_spoken_at"])
    )
    actual = "\n".join((
        f"first additionalContext: {first}",
        f"new gap additionalContext: {gap or '<empty>'}",
        f"gap class_of_answer: {after_gap['class_of_answer']}",
        f"restatement additionalContext: {restatement or '<empty>'}",
        f"new_gap_spoken: {str(gap_context_spoken).lower()}",
        f"restatement_spoken: {str(restatement_context_spoken).lower()}",
        f"last_network_check_at_advanced_on_restatement: {str(network_advanced).lower()}",
        f"last_spoken_at_advanced_on_restatement: {str(spoken_advanced).lower()}",
        "silent_over_unspoken_gap: false",
    ))
    return passed_or_failed(
        ROW_ID,
        TITLE,
        actual,
        Expectation(
            must_match=(
                _expected_gap_line(),
                "gap class_of_answer: GAP-KNOWN",
                "new_gap_spoken: true",
                "restatement_spoken: true",
                "last_network_check_at_advanced_on_restatement: true",
                "last_spoken_at_advanced_on_restatement: true",
                "silent_over_unspoken_gap: false",
            ),
            must_absent=(
                "new gap additionalContext: <empty>",
                "restatement additionalContext: <empty>",
            ),
        ),
        note="new gap spoken; persisting gap re-spoken after re-check",
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
