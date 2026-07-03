from __future__ import annotations

import subprocess
from pathlib import Path

import pytest

from teamctx.git_context import (
    detect_branch,
    detect_forge_repo,
    detect_repo,
    parse_github_repo,
    parse_gitlab_repo,
    repo_relative_path,
    resolve_project_root,
)


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


@pytest.mark.parametrize(
    ("value", "expected"),
    [
        ("owner/name", "owner/name"),
        ("owner/name/", "owner/name"),
        ("group/sub/project", "group/sub/project"),
        ("https://gitlab.com/owner/name", "owner/name"),
        ("https://gitlab.com/owner/name.git", "owner/name"),
        ("https://gitlab.com/group/sub/project.git", "group/sub/project"),
        ("git@gitlab.com:owner/name.git", "owner/name"),
        ("git@gitlab.com:group/sub/project.git", "group/sub/project"),
        ("ssh://git@gitlab.com/group/sub/project.git", "group/sub/project"),
    ],
)
def test_parse_gitlab_repo_accepts_gitlab(value: str, expected: str) -> None:
    assert parse_gitlab_repo(value) == expected


@pytest.mark.parametrize(
    "value",
    [
        "https://github.com/owner/name",
        "git@github.com:owner/name.git",
        "owner",
        "",
        "https://gitlab.com/owner",
        "../sibling",
        "owner/../project",
        "owner/na me",
    ],
)
def test_parse_gitlab_repo_rejects(value: str) -> None:
    assert parse_gitlab_repo(value) is None


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


@pytest.mark.parametrize(
    ("origin", "expected"),
    [
        ("git@github.com:acme/widgets.git", ("acme/widgets", "github")),
        ("https://github.com/acme/widgets.git", ("acme/widgets", "github")),
        ("git@gitlab.com:acme/widgets.git", ("acme/widgets", "gitlab")),
        ("https://gitlab.com/group/sub/project.git", ("group/sub/project", "gitlab")),
    ],
)
def test_detect_forge_repo_by_origin_host(
    tmp_path: Path, origin: str, expected: tuple[str, str]
) -> None:
    _init_repo(tmp_path)
    subprocess.run(
        ["git", "-C", str(tmp_path), "remote", "add", "origin", origin],
        check=True,
    )

    assert detect_forge_repo(tmp_path) == expected


def test_detect_forge_repo_none_for_unrecognized_host(tmp_path: Path) -> None:
    _init_repo(tmp_path)
    subprocess.run(
        ["git", "-C", str(tmp_path), "remote", "add", "origin", "git@example.com:acme/widgets.git"],
        check=True,
    )

    assert detect_forge_repo(tmp_path) is None
    assert detect_repo(tmp_path) is None


def test_detect_returns_none_outside_a_repo(tmp_path: Path) -> None:
    assert detect_repo(tmp_path) is None
    assert detect_forge_repo(tmp_path) is None
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


def test_resolve_project_root_prefers_override(tmp_path: Path) -> None:
    override = tmp_path / "explicit"
    override.mkdir()
    assert resolve_project_root(start=tmp_path, override=override) == override


def test_resolve_project_root_falls_back_to_start_when_non_git(tmp_path: Path) -> None:
    # tmp_path is not a git repo, so toplevel is None and we get start back.
    assert resolve_project_root(start=tmp_path) == tmp_path


def test_resolve_project_root_uses_git_toplevel(tmp_path: Path) -> None:
    subprocess.run(["git", "-C", str(tmp_path), "init", "-q"], check=True)
    sub = tmp_path / "src"
    sub.mkdir()
    # From a subdirectory, the resolved root is the repo toplevel, not the subdir.
    assert resolve_project_root(start=sub).resolve() == tmp_path.resolve()


def test_repo_relative_path_makes_paths_repo_relative(tmp_path: Path) -> None:
    _init_repo(tmp_path)
    # a leading ./ and an absolute path within the repo both normalize to repo-relative POSIX,
    # so a caller's --path matches the broker's repo-relative signal paths.
    assert repo_relative_path(tmp_path, "./docs/old.md") == "docs/old.md"
    assert repo_relative_path(tmp_path, str(tmp_path / "src" / "a.py")) == "src/a.py"
    assert repo_relative_path(tmp_path, "src/a.py") == "src/a.py"  # idempotent


def test_repo_relative_path_cleans_dot_slash_outside_a_repo(tmp_path: Path) -> None:
    # not a git tree: still clean the leading ./ and never raise.
    assert repo_relative_path(tmp_path, "./docs/old.md") == "docs/old.md"
