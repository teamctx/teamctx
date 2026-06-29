from __future__ import annotations

import subprocess
from pathlib import Path

import pytest

from teamctx.git_context import detect_branch, detect_repo, parse_github_repo


@pytest.mark.parametrize(
    ("value", "expected"),
    [
        ("owner/name", "owner/name"),
        ("owner/name/", "owner/name"),
        ("https://github.com/owner/name", "owner/name"),
        ("https://github.com/owner/name.git", "owner/name"),
        ("git@github.com:owner/name.git", "owner/name"),
        ("ssh://git@github.com/owner/name.git", "owner/name"),
        ("owner/.github", "owner/.github"),
    ],
)
def test_parse_github_repo_accepts_github(value: str, expected: str) -> None:
    assert parse_github_repo(value) == expected


@pytest.mark.parametrize(
    "value",
    [
        "https://gitlab.com/owner/name",      # non-github host fails closed
        "git@gitlab.com:owner/name.git",
        "ssh://git@gitlab.com/owner/name.git",
        "owner",                               # one segment
        "owner/name/extra",                    # three segments
        "",                                    # empty
        "https://github.com/owner",            # github but not a full slug
        "../sibling",                          # path-traversal segment rejected
        "../name",
        "owner/na me",                         # invalid character (space)
    ],
)
def test_parse_github_repo_rejects(value: str) -> None:
    assert parse_github_repo(value) is None


def _init_repo(root: Path) -> None:
    subprocess.run(["git", "-C", str(root), "init", "-q"], check=True)
    subprocess.run(["git", "-C", str(root), "config", "user.email", "t@t"], check=True)
    subprocess.run(["git", "-C", str(root), "config", "user.name", "t"], check=True)
    (root / "f.txt").write_text("x", encoding="utf-8")
    subprocess.run(["git", "-C", str(root), "add", "."], check=True)
    subprocess.run(["git", "-C", str(root), "commit", "-qm", "init"], check=True)


def test_detect_repo_and_branch_in_a_real_repo(tmp_path: Path) -> None:
    _init_repo(tmp_path)
    subprocess.run(
        ["git", "-C", str(tmp_path), "remote", "add", "origin",
         "git@github.com:acme/widgets.git"], check=True,
    )
    subprocess.run(["git", "-C", str(tmp_path), "checkout", "-qb", "feature"], check=True)
    assert detect_repo(tmp_path) == "acme/widgets"
    assert detect_branch(tmp_path) == "feature"


def test_detect_returns_none_outside_a_repo(tmp_path: Path) -> None:
    assert detect_repo(tmp_path) is None
    assert detect_branch(tmp_path) is None


def test_detect_repo_none_without_origin(tmp_path: Path) -> None:
    _init_repo(tmp_path)  # a repo, but no origin remote added
    assert detect_repo(tmp_path) is None
    assert detect_branch(tmp_path) is not None  # branch still detectable


def test_detect_branch_none_when_detached(tmp_path: Path) -> None:
    _init_repo(tmp_path)
    head = subprocess.run(
        ["git", "-C", str(tmp_path), "rev-parse", "HEAD"],
        capture_output=True, text=True, check=True,
    ).stdout.strip()
    subprocess.run(["git", "-C", str(tmp_path), "checkout", "-q", head], check=True)
    assert detect_branch(tmp_path) is None
