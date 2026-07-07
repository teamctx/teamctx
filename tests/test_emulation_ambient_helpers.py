from __future__ import annotations

import json
from pathlib import Path

from emulation.actors import PersistentAmbientActor
from emulation.ambient_helpers import ambient_state_file, backdate_baseline, load_ambient_state


def test_persistent_ambient_actor_reuses_session_id_and_state_dir(tmp_path: Path) -> None:
    actor = PersistentAmbientActor(state_dir=tmp_path / "ambient", session_id="delta-session")

    first = actor.pretooluse_event(cwd=tmp_path, file_path="src/app.py")
    second = actor.pretooluse_event(cwd=tmp_path, file_path="src/other.py")
    env = actor.env(api_root="http://127.0.0.1:12345").as_dict()

    assert first["session_id"] == second["session_id"] == "delta-session"
    assert first["tool_input"] == {"file_path": "src/app.py"}
    assert second["tool_input"] == {"file_path": "src/other.py"}
    assert env["TEAMCTX_AMBIENT_STATE"] == str(tmp_path / "ambient")
    assert env["TEAMCTX_GITHUB_API_ROOT"] == "http://127.0.0.1:12345"


def test_backdate_baseline_rewrites_times_without_changing_digest_or_material(
    tmp_path: Path,
) -> None:
    state_dir = tmp_path / "ambient"
    state_dir.mkdir()
    state_file = ambient_state_file(state_dir, "delta/session!*")
    state_file.write_text(
        json.dumps({
            "schema_version": "teamctx.ambient_state.v2",
            "session_id": "delta/session!*",
            "baselines": {
                "key-1": {
                    "key": "key-1",
                    "content_digest": "digest-1",
                    "class_of_answer": "GOOD",
                    "last_network_check_at": 1000.0,
                    "last_spoken_at": 900.0,
                    "material": {
                        "checks": [
                            {
                                "check": "conflict",
                                "status": "clear",
                                "note": None,
                                "findings": [],
                            }
                        ]
                    },
                }
            },
        }),
        encoding="utf-8",
    )

    backdate_baseline(state_dir, "delta/session!*", seconds=120)

    state = load_ambient_state(state_dir, "delta/session!*")
    baseline = state["baselines"]["key-1"]
    assert baseline["last_network_check_at"] == 880.0
    assert baseline["last_spoken_at"] == 780.0
    assert baseline["content_digest"] == "digest-1"
    assert baseline["material"] == {
        "checks": [
            {"check": "conflict", "status": "clear", "note": None, "findings": []}
        ]
    }
