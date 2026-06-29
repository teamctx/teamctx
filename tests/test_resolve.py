from __future__ import annotations

import json
import subprocess
from pathlib import Path

import pytest

import teamctx.resolve as resolve_mod
from teamctx.resolve import WorkStartResolutionError, resolve_work_start_inputs


def _write_config(root: Path, **work_start: str) -> None:
    (root / ".teamctx").mkdir(parents=True, exist_ok=True)
    (root / ".teamctx" / "config.json").write_text(
        json.dumps({"schema_version": "teamctx.project_config.v0", "work_start": work_start}),
        encoding="utf-8",
    )


def test_explicit_repo_wins_over_config_and_git(monkeypatch, tmp_path: Path) -> None:
    _write_config(tmp_path, repo="from/config")
    monkeypatch.setattr(resolve_mod, "detect_repo", lambda root: "from/git")
    monkeypatch.setattr(resolve_mod, "detect_branch", lambda root: None)
    inputs = resolve_work_start_inputs(paths=("src/x.py",), repo="from/explicit", root=tmp_path)
    assert inputs.repo == "from/explicit"


def test_config_repo_wins_over_git(monkeypatch, tmp_path: Path) -> None:
    _write_config(tmp_path, repo="from/config")
    monkeypatch.setattr(resolve_mod, "detect_repo", lambda root: "from/git")
    monkeypatch.setattr(resolve_mod, "detect_branch", lambda root: None)
    inputs = resolve_work_start_inputs(paths=("src/x.py",), root=tmp_path)
    assert inputs.repo == "from/config"


def test_git_used_when_no_explicit_or_config(monkeypatch, tmp_path: Path) -> None:
    monkeypatch.setattr(resolve_mod, "detect_repo", lambda root: "from/git")
    monkeypatch.setattr(resolve_mod, "detect_branch", lambda root: "feature")
    inputs = resolve_work_start_inputs(paths=("src/x.py",), root=tmp_path)
    assert inputs.repo == "from/git"
    assert inputs.branch == "feature"


def test_missing_repo_raises(monkeypatch, tmp_path: Path) -> None:
    monkeypatch.setattr(resolve_mod, "detect_repo", lambda root: None)
    monkeypatch.setattr(resolve_mod, "detect_branch", lambda root: None)
    with pytest.raises(WorkStartResolutionError):
        resolve_work_start_inputs(paths=("src/x.py",), root=tmp_path)


def test_branch_from_git_not_config_and_docs_root_from_config(monkeypatch, tmp_path: Path) -> None:
    _write_config(tmp_path, repo="from/config", docs_root="docs")
    monkeypatch.setattr(resolve_mod, "detect_repo", lambda root: None)
    monkeypatch.setattr(resolve_mod, "detect_branch", lambda root: "detected")
    inputs = resolve_work_start_inputs(paths=("src/x.py",), root=tmp_path)
    assert inputs.branch == "detected"
    assert inputs.docs_root == "docs"


def test_explicit_docs_root_wins_over_config(monkeypatch, tmp_path: Path) -> None:
    _write_config(tmp_path, repo="from/config", docs_root="from/config")
    monkeypatch.setattr(resolve_mod, "detect_repo", lambda root: None)
    monkeypatch.setattr(resolve_mod, "detect_branch", lambda root: None)
    inputs = resolve_work_start_inputs(
        paths=("src/x.py",), docs_root="from/explicit", root=tmp_path
    )
    assert inputs.docs_root == "from/explicit"


def test_resolve_rejects_non_github_explicit_repo(tmp_path: Path) -> None:
    with pytest.raises(WorkStartResolutionError):
        resolve_work_start_inputs(paths=("a.py",), repo="https://gitlab.com/o/n", root=tmp_path)


def test_resolves_from_a_real_repo_and_config(tmp_path: Path) -> None:
    subprocess.run(["git", "-C", str(tmp_path), "init", "-q"], check=True)
    subprocess.run(["git", "-C", str(tmp_path), "config", "user.email", "t@t"], check=True)
    subprocess.run(["git", "-C", str(tmp_path), "config", "user.name", "t"], check=True)
    (tmp_path / "f.txt").write_text("x", encoding="utf-8")
    subprocess.run(["git", "-C", str(tmp_path), "add", "."], check=True)
    subprocess.run(["git", "-C", str(tmp_path), "commit", "-qm", "i"], check=True)
    subprocess.run(["git", "-C", str(tmp_path), "checkout", "-qb", "feat"], check=True)
    subprocess.run(
        ["git", "-C", str(tmp_path), "remote", "add", "origin",
         "https://github.com/acme/widgets.git"], check=True,
    )
    _write_config(tmp_path, docs_root="docs")
    inputs = resolve_work_start_inputs(paths=("src/x.py",), root=tmp_path)
    assert inputs.repo == "acme/widgets"
    assert inputs.branch == "feat"
    assert inputs.docs_root == "docs"
