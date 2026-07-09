"""Row 14: Lawful silence.

An unchanged world after interval expiry must be silent only after a real re-check. The row proves
that by asserting empty additionalContext plus unchanged content digest and an advanced
last_network_check_at in the state file.
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
)

ROW_ID = "14"
TITLE = "Lawful silence after re-check"


def _row(tmp: Path) -> RowResult:
    repo = build_delta_repo(tmp / "repo")
    actor = PersistentAmbientActor(state_dir=tmp / "ambient", session_id=DELTA_SESSION)
    with MockGitHub(clear_fixtures()) as server:
        env = actor.env(api_root=server.api_root)
        event = actor.pretooluse_event(cwd=repo.root, file_path=DELTA_FILE)
        first = run_hook(event, cwd=repo.root, env=env)

        backdate_baseline(actor.state_dir, actor.session_id, seconds=120)
        before = only_baseline(actor.state_dir, actor.session_id)
        second = run_hook(event, cwd=repo.root, env=env)
        after = only_baseline(actor.state_dir, actor.session_id)

    digest_unchanged = after["content_digest"] == before["content_digest"]
    network_advanced = (
        float(after["last_network_check_at"]) > float(before["last_network_check_at"])
    )
    actual = "\n".join((
        f"first additionalContext: {first}",
        f"second additionalContext: {second or '<empty>'}",
        f"content_digest_unchanged: {str(digest_unchanged).lower()}",
        f"last_network_check_at_advanced: {str(network_advanced).lower()}",
    ))
    return passed_or_failed(
        ROW_ID,
        TITLE,
        actual,
        Expectation(
            must_match=(
                "second additionalContext: <empty>",
                "content_digest_unchanged: true",
                "last_network_check_at_advanced: true",
            ),
            must_absent=("since you started:", "teamctx: before you edit"),
        ),
        note="silence-after-recheck: digest unchanged; last_network_check_at advanced",
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
