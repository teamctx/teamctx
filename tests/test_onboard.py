from __future__ import annotations

import subprocess
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent


def test_repo_gitignore_allows_tracking_teamctx_config() -> None:
    # .teamctx/config.json must be trackable in teamctx's own repo (for the dogfood fixture and so
    # onboard's own pattern matches). git check-ignore exits 1 when a path is NOT ignored.
    result = subprocess.run(
        ["git", "check-ignore", "--no-index", ".teamctx/config.json"],
        cwd=ROOT, capture_output=True, text=True,
    )
    assert result.returncode == 1, f"config.json is still ignored: {result.stdout!r}"
    # local state IS still ignored:
    ignored = subprocess.run(
        ["git", "check-ignore", "--no-index", ".teamctx/state.sqlite3"],
        cwd=ROOT, capture_output=True, text=True,
    )
    assert ignored.returncode == 0
