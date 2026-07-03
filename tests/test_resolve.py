from __future__ import annotations

import json
import subprocess
from pathlib import Path

import pytest

import teamctx.resolve as resolve_mod
from teamctx.discover import DerivedIssues
from teamctx.resolve import WorkStartResolutionError, resolve_work_start_inputs
from teamctx.runner import build_request_context


def _write_config(root: Path, **work_start: str) -> None:
    (root / ".teamctx").mkdir(parents=True, exist_ok=True)
    (root / ".teamctx" / "config.json").write_text(
        json.dumps({"schema_version": "teamctx.project_config.v0", "work_start": work_start}),
        encoding="utf-8",
    )


def test_explicit_repo_wins_over_config_and_git(monkeypatch, tmp_path: Path) -> None:
    _write_config(tmp_path, repo="from/config")
    monkeypatch.setattr(resolve_mod, "detect_forge_repo", lambda root: ("from/git", "github"))
    monkeypatch.setattr(resolve_mod, "detect_branch", lambda root: None)
    inputs = resolve_work_start_inputs(paths=("src/x.py",), repo="from/explicit", root=tmp_path)
    assert inputs.repo == "from/explicit"
    assert inputs.forge == "github"


def test_config_repo_wins_over_git(monkeypatch, tmp_path: Path) -> None:
    _write_config(tmp_path, repo="from/config")
    monkeypatch.setattr(resolve_mod, "detect_forge_repo", lambda root: ("from/git", "github"))
    monkeypatch.setattr(resolve_mod, "detect_branch", lambda root: None)
    inputs = resolve_work_start_inputs(paths=("src/x.py",), root=tmp_path)
    assert inputs.repo == "from/config"
    assert inputs.forge == "github"


def test_git_used_when_no_explicit_or_config(monkeypatch, tmp_path: Path) -> None:
    monkeypatch.setattr(resolve_mod, "detect_forge_repo", lambda root: ("from/git", "github"))
    monkeypatch.setattr(resolve_mod, "detect_branch", lambda root: "feature")
    inputs = resolve_work_start_inputs(paths=("src/x.py",), root=tmp_path)
    assert inputs.repo == "from/git"
    assert inputs.forge == "github"
    assert inputs.branch == "feature"


def test_missing_repo_raises(monkeypatch, tmp_path: Path) -> None:
    monkeypatch.setattr(resolve_mod, "detect_forge_repo", lambda root: None)
    monkeypatch.setattr(resolve_mod, "detect_branch", lambda root: None)
    with pytest.raises(WorkStartResolutionError):
        resolve_work_start_inputs(paths=("src/x.py",), root=tmp_path)


def test_branch_from_git_not_config_and_docs_root_from_config(monkeypatch, tmp_path: Path) -> None:
    _write_config(tmp_path, repo="from/config", docs_root="docs")
    monkeypatch.setattr(resolve_mod, "detect_forge_repo", lambda root: None)
    monkeypatch.setattr(resolve_mod, "detect_branch", lambda root: "detected")
    inputs = resolve_work_start_inputs(paths=("src/x.py",), root=tmp_path)
    assert inputs.branch == "detected"
    assert inputs.docs_root == "docs"


def test_explicit_docs_root_wins_over_config(monkeypatch, tmp_path: Path) -> None:
    _write_config(tmp_path, repo="from/config", docs_root="from/config")
    monkeypatch.setattr(resolve_mod, "detect_forge_repo", lambda root: None)
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
    assert inputs.forge == "github"
    assert inputs.branch == "feat"
    assert inputs.docs_root == "docs"


def test_resolve_normalizes_request_paths_repo_relative(tmp_path: Path) -> None:
    # a caller's raw --path (with a ./ prefix) is normalized to repo-relative POSIX so it
    # matches the broker's signal paths; without this an in-scope doc/PR/gate would be missed.
    inputs = resolve_work_start_inputs(
        paths=("./docs/old.md", "src/a.py"), repo="owner/name", root=tmp_path
    )
    assert inputs.paths == ("docs/old.md", "src/a.py")


def test_resolve_github_repo_shared_precedence_and_normalization() -> None:
    from teamctx.resolve import resolve_github_repo
    assert resolve_github_repo("a/b", "c/d", "e/f") == ("a/b", None)  # explicit wins
    assert resolve_github_repo(None, "c/d", "e/f") == ("c/d", None)  # then config
    assert resolve_github_repo(None, None, "e/f") == ("e/f", None)  # then git-detect
    assert resolve_github_repo("", "", "e/f") == ("e/f", None)  # empty strings are absent
    assert resolve_github_repo("https://github.com/o/p.git", None, None)[0] == "o/p"  # normalized
    repo, err = resolve_github_repo("not-a-repo", None, None)
    assert repo is None and err is not None  # invalid -> error
    repo, err = resolve_github_repo(None, None, None)
    assert repo is None and err is not None  # nothing resolves -> error


def test_resolve_forge_repo_shared_precedence_and_normalization() -> None:
    from teamctx.resolve import resolve_forge_repo

    assert resolve_forge_repo("a/b", "c/d", "github", ("e/f", "gitlab")) == (
        ("a/b", "github"), None,
    )
    assert resolve_forge_repo(None, "group/sub/project", "gitlab", ("e/f", "github")) == (
        ("group/sub/project", "gitlab"), None,
    )
    assert resolve_forge_repo(None, None, None, ("group/sub/project", "gitlab")) == (
        ("group/sub/project", "gitlab"), None,
    )
    assert resolve_forge_repo("https://github.com/o/p.git", None, None, None) == (
        ("o/p", "github"), None,
    )
    resolved, err = resolve_forge_repo(None, "group/sub/project", "github", None)
    assert resolved is None and err is not None


@pytest.mark.parametrize(
    ("config_repo", "config_forge", "detected", "expected"),
    [
        (None, None, ("from/git", "github"), ("from/git", "github")),
        (None, None, ("group/sub/project", "gitlab"), ("group/sub/project", "gitlab")),
        ("from/config", "github", ("group/sub/project", "gitlab"), ("from/config", "github")),
        (
            "group/sub/project",
            "gitlab",
            ("from/git", "github"),
            ("group/sub/project", "gitlab"),
        ),
        (
            "https://gitlab.com/group/sub/project.git",
            "gitlab",
            None,
            ("group/sub/project", "gitlab"),
        ),
        ("acme/widgets", "gitlab", ("acme/widgets", "github"), ("acme/widgets", "gitlab")),
    ],
)
def test_resolve_work_start_inputs_parity_matrix_includes_forge(
    monkeypatch,
    tmp_path: Path,
    config_repo: str | None,
    config_forge: str | None,
    detected: tuple[str, str] | None,
    expected: tuple[str, str],
) -> None:
    if config_repo is not None or config_forge is not None:
        fields = {}
        if config_repo is not None:
            fields["repo"] = config_repo
        if config_forge is not None:
            fields["forge"] = config_forge
        _write_config(tmp_path, **fields)
    monkeypatch.setattr(resolve_mod, "detect_forge_repo", lambda root: detected)
    monkeypatch.setattr(resolve_mod, "detect_branch", lambda root: None)

    inputs = resolve_work_start_inputs(paths=("src/x.py",), root=tmp_path)

    assert (inputs.repo, inputs.forge) == expected


def test_resolve_derives_issues_since_and_provenance(monkeypatch, tmp_path: Path) -> None:
    monkeypatch.setattr(resolve_mod, "detect_forge_repo", lambda root: ("from/git", "github"))
    monkeypatch.setattr(resolve_mod, "detect_branch", lambda root: "feature")
    monkeypatch.setattr(
        resolve_mod,
        "derive_issues",
        lambda root: DerivedIssues((("#42", "your branch name"),), capped=False),
    )
    monkeypatch.setattr(
        resolve_mod,
        "derive_since",
        lambda root: ("2026-07-01T09:15:00Z", "when you branched (merge-base abc1234)"),
    )

    inputs = resolve_work_start_inputs(paths=("src/x.py",), root=tmp_path)

    assert inputs.issues == ("#42",)
    assert inputs.since == "2026-07-01T09:15:00Z"
    assert inputs.input_provenance == (
        ("issue:#42", "your branch name"),
        ("since", "when you branched (merge-base abc1234)"),
    )
    request = build_request_context(inputs, observed_at="2026-07-03T00:00:00Z")
    assert request.input_provenance == {
        "issue:#42": "your branch name",
        "since": "when you branched (merge-base abc1234)",
    }


def test_explicit_issue_and_since_suppress_derivation(monkeypatch, tmp_path: Path) -> None:
    def fail_derive(root: Path) -> None:
        raise AssertionError("derivation should be disabled by explicit inputs")

    monkeypatch.setattr(resolve_mod, "derive_issues", fail_derive)
    monkeypatch.setattr(resolve_mod, "derive_since", fail_derive)

    inputs = resolve_work_start_inputs(
        paths=("src/x.py",),
        repo="owner/name",
        branch="explicit",
        issues=("#9",),
        since="2026-07-01",
        root=tmp_path,
    )

    assert inputs.issues == ("#9",)
    assert inputs.since == "2026-07-01"
    assert inputs.input_provenance == ()


def test_bad_explicit_since_raises_pinned_message(tmp_path: Path) -> None:
    with pytest.raises(WorkStartResolutionError) as exc:
        resolve_work_start_inputs(
            paths=("src/x.py",),
            repo="owner/name",
            since="July 1",
            root=tmp_path,
        )

    assert str(exc.value) == (
        "--since 'July 1' is not an ISO-8601 timestamp "
        "(e.g. 2026-07-01 or 2026-07-01T12:00:00Z)."
    )
