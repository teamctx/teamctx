from __future__ import annotations

import os
import subprocess
from pathlib import Path

from teamctx.discover import derive_issues, derive_since


def _git(root: Path, *args: str, env: dict[str, str] | None = None) -> str:
    result = subprocess.run(
        ["git", "-C", str(root), *args],
        check=True,
        capture_output=True,
        text=True,
        env={**os.environ, **(env or {})},
    )
    return result.stdout.strip()


def _init_repo(root: Path) -> None:
    _git(root, "init", "-q", "-b", "main")
    _git(root, "config", "user.email", "t@t")
    _git(root, "config", "user.name", "t")
    _commit(root, "base", "2026-07-01T09:15:00+00:00")
    _git(root, "update-ref", "refs/remotes/origin/main", "HEAD")
    _git(root, "symbolic-ref", "refs/remotes/origin/HEAD", "refs/remotes/origin/main")


def _commit(root: Path, message: str, date: str = "2026-07-01T10:00:00+00:00") -> None:
    counter = root / "f.txt"
    existing = counter.read_text(encoding="utf-8") if counter.exists() else ""
    counter.write_text(existing + f"{message}\n", encoding="utf-8")
    _git(root, "add", "f.txt")
    env = {
        "GIT_AUTHOR_DATE": date,
        "GIT_COMMITTER_DATE": date,
    }
    _git(root, "commit", "-qm", message, env=env)


def _issue_pairs(root: Path) -> tuple[tuple[str, str], ...]:
    return derive_issues(root).issues


def test_branch_issue_derivation_matrix(tmp_path: Path) -> None:
    for branch in ("123-fix", "feat/123-x", "issue-123", "fix/#123"):
        repo = tmp_path / branch.replace("/", "_").replace("#", "hash")
        repo.mkdir()
        _init_repo(repo)
        _git(repo, "checkout", "-qb", branch)

        assert _issue_pairs(repo) == (("#123", "your branch name"),)


def test_branch_jira_key_derivation_removes_span_before_numeric_scan(tmp_path: Path) -> None:
    for branch, expected in (
        ("PROJ-123", (("PROJ-123", "your branch name"),)),
        ("PROJ-123-fix", (("PROJ-123", "your branch name"),)),
        ("feat/ABC-7", (("ABC-7", "your branch name"),)),
        ("feat/ABC-7/42-fix", (("#42", "your branch name"), ("ABC-7", "your branch name"))),
        ("fix/#42-PROJ-123", (("#42", "your branch name"), ("PROJ-123", "your branch name"))),
    ):
        repo = tmp_path / branch.replace("/", "_").replace("#", "hash")
        repo.mkdir()
        _init_repo(repo)
        _git(repo, "checkout", "-qb", branch)

        assert _issue_pairs(repo) == expected


def test_branch_release_shapes_do_not_derive(tmp_path: Path) -> None:
    for branch in ("v2", "release-2.0", "feature"):
        repo = tmp_path / branch.replace("/", "_").replace(".", "_")
        repo.mkdir()
        _init_repo(repo)
        _git(repo, "checkout", "-qb", branch)

        assert _issue_pairs(repo) == ()


def test_trailer_union_dedupe_numeric_sort_and_branch_wins(tmp_path: Path) -> None:
    _init_repo(tmp_path)
    _git(tmp_path, "checkout", "-qb", "feat/12-x")
    _commit(tmp_path, "fix auth\n\nCloses #34\nFixes #12\nresolves #7")

    assert _issue_pairs(tmp_path) == (
        ("#7", "a commit message trailer"),
        ("#12", "your branch name"),
        ("#34", "a commit message trailer"),
    )


def test_trailers_accept_jira_keys_and_remove_span_before_numeric_scan(tmp_path: Path) -> None:
    _init_repo(tmp_path)
    _git(tmp_path, "checkout", "-qb", "feature")
    _commit(tmp_path, "fix auth\n\nCloses PROJ-123\nFixes #12\nresolves ABC-7")

    assert _issue_pairs(tmp_path) == (
        ("#12", "a commit message trailer"),
        ("ABC-7", "a commit message trailer"),
        ("PROJ-123", "a commit message trailer"),
    )


def test_branch_provenance_wins_over_trailer_for_jira_key(tmp_path: Path) -> None:
    _init_repo(tmp_path)
    _git(tmp_path, "checkout", "-qb", "PROJ-123-fix")
    _commit(tmp_path, "fix auth\n\nCloses PROJ-123")

    assert _issue_pairs(tmp_path) == (("PROJ-123", "your branch name"),)


def test_more_than_five_derived_issues_are_capped(tmp_path: Path) -> None:
    _init_repo(tmp_path)
    _git(tmp_path, "checkout", "-qb", "feat/42-x")
    _commit(
        tmp_path,
        "many issues\n\n"
        "Closes #8\nFixes #7\nResolves #6\nCloses #5\nFixes #4\nResolves #3",
    )

    derived = derive_issues(tmp_path)

    assert derived.capped is True
    assert derived.issues == (
        ("#3", "a commit message trailer"),
        ("#4", "a commit message trailer"),
        ("#5", "a commit message trailer"),
        ("#6", "a commit message trailer"),
        ("#7", "a commit message trailer"),
    )


def test_no_default_branch_detached_head_and_non_git_are_honest_absence(
    tmp_path: Path,
) -> None:
    no_default = tmp_path / "no_default"
    no_default.mkdir()
    _init_repo(no_default)
    _git(no_default, "update-ref", "-d", "refs/remotes/origin/main")
    _git(no_default, "symbolic-ref", "--delete", "refs/remotes/origin/HEAD")

    detached = tmp_path / "detached"
    detached.mkdir()
    _init_repo(detached)
    _git(detached, "checkout", "-qb", "feat/123-x")
    head = _git(detached, "rev-parse", "HEAD")
    _git(detached, "checkout", "-q", head)

    non_git = tmp_path / "non_git"
    non_git.mkdir()

    for repo in (no_default, detached, non_git):
        assert derive_issues(repo).issues == ()
        assert derive_issues(repo).capped is False
        assert derive_since(repo) is None


def test_since_uses_merge_base_committer_timestamp_and_provenance(tmp_path: Path) -> None:
    _init_repo(tmp_path)
    base = _git(tmp_path, "rev-parse", "--short", "origin/main")
    _git(tmp_path, "checkout", "-qb", "42-fix")
    _commit(tmp_path, "work", "2026-07-02T12:00:00+00:00")

    assert derive_since(tmp_path) == (
        "2026-07-01T09:15:00Z",
        f"when you branched (merge-base {base})",
    )
