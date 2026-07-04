"""Helpers for ambient delta rows in the offline emulation harness."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any


def ambient_state_file(state_dir: Path, session_id: str) -> Path:
    safe = "".join(c for c in session_id if c.isalnum() or c in "-_")
    return state_dir / f"{safe or 'session'}.json"


def load_ambient_state(state_dir: Path, session_id: str) -> dict[str, Any]:
    path = ambient_state_file(state_dir, session_id)
    data = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(data, dict):
        raise RuntimeError(f"ambient state was not an object: {path}")
    baselines = data.get("baselines")
    if not isinstance(baselines, dict) or not baselines:
        raise RuntimeError(f"ambient state has no baselines: {path}")
    return data


def backdate_baseline(state_dir: Path, session_id: str, seconds: float) -> None:
    """Move every baseline in ``session_id`` back by ``seconds`` without sleeping."""

    path = ambient_state_file(state_dir, session_id)
    data = load_ambient_state(state_dir, session_id)
    for baseline in data["baselines"].values():
        if not isinstance(baseline, dict):
            raise RuntimeError(f"ambient baseline was not an object: {path}")
        baseline["last_network_check_at"] = float(baseline["last_network_check_at"]) - seconds
        baseline["last_spoken_at"] = float(baseline["last_spoken_at"]) - seconds
    text = json.dumps(data, sort_keys=True, separators=(",", ":")) + "\n"
    path.write_text(text, encoding="utf-8")
