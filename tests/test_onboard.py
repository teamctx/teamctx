from __future__ import annotations

import os
import subprocess
from pathlib import Path

import pytest

from teamctx.onboard import CLAUDE_MD_SNIPPET, _atomic_write

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


def test_snippet_is_honest_about_what_auto_fires() -> None:
    assert "open pull requests" in CLAUDE_MD_SNIPPET or "open PRs" in CLAUDE_MD_SNIPPET
    assert "failing checks" in CLAUDE_MD_SNIPPET
    # must NOT overclaim the checks that do not auto-fire yet:
    assert "changed specs" not in CLAUDE_MD_SNIPPET
    assert "superseded docs" not in CLAUDE_MD_SNIPPET


def test_atomic_write_creates_and_overwrites(tmp_path: Path) -> None:
    target = tmp_path / "sub" / "f.txt"
    _atomic_write(target, "one\n")
    assert target.read_text(encoding="utf-8") == "one\n"
    _atomic_write(target, "two\n")
    assert target.read_text(encoding="utf-8") == "two\n"
    assert [p.name for p in target.parent.iterdir()] == ["f.txt"]  # no leftover temp


def test_atomic_write_is_failure_atomic(tmp_path: Path, monkeypatch) -> None:
    target = tmp_path / "f.txt"
    _atomic_write(target, "original\n")

    def _boom(src: object, dst: object) -> None:
        raise OSError("replace failed")

    monkeypatch.setattr(os, "replace", _boom)
    with pytest.raises(OSError):
        _atomic_write(target, "new\n")
    assert target.read_text(encoding="utf-8") == "original\n"  # original intact
    assert [p.name for p in target.parent.iterdir()] == ["f.txt"]  # temp cleaned up
