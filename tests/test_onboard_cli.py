from __future__ import annotations

import subprocess
from pathlib import Path

from click.testing import CliRunner

from teamctx.cli import main


def _github_repo(root: Path) -> None:
    subprocess.run(["git", "-C", str(root), "init", "-q"], check=True)
    subprocess.run(
        ["git", "-C", str(root), "remote", "add", "origin", "git@github.com:acme/widgets.git"],
        check=True,
    )


def test_onboard_happy_path(tmp_path: Path, monkeypatch) -> None:
    _github_repo(tmp_path)
    monkeypatch.chdir(tmp_path)
    # network-free: no token, so verify_health reports "no credential" without a live fetch.
    monkeypatch.delenv("GITHUB_TOKEN", raising=False)
    monkeypatch.setenv("TEAMCTX_DISABLE_GH_AUTH", "1")
    result = CliRunner().invoke(main, ["onboard"], catch_exceptions=False)
    assert result.exit_code == 0, result.output
    assert (tmp_path / ".teamctx" / "config.json").exists()
    assert (tmp_path / "CLAUDE.md").exists()
    assert "acme/widgets" in result.output
    assert "work-start" in result.output  # the next step


def test_onboard_dry_run_writes_nothing(tmp_path: Path, monkeypatch) -> None:
    _github_repo(tmp_path)
    monkeypatch.chdir(tmp_path)
    monkeypatch.setenv("TEAMCTX_DISABLE_GH_AUTH", "1")
    result = CliRunner().invoke(main, ["onboard", "--dry-run"], catch_exceptions=False)
    assert result.exit_code == 0, result.output
    assert not (tmp_path / ".teamctx").exists()
    assert "dry run" in result.output.lower() or "would" in result.output.lower()


def test_onboard_non_github_repo_errors_with_fix(tmp_path: Path, monkeypatch) -> None:
    subprocess.run(["git", "-C", str(tmp_path), "init", "-q"], check=True)  # no origin
    monkeypatch.chdir(tmp_path)
    result = CliRunner().invoke(main, ["onboard"])
    assert result.exit_code != 0
    assert "--repo" in result.output
