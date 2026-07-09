from __future__ import annotations

import json
import subprocess
from pathlib import Path

from teamctx.ambient import compute_key
from teamctx.config_failure import (
    COMMIT_CONFIG_TO_ACTIVATE_LINE,
    CONFIG_DIRTY_NOTE,
)
from teamctx.resolve import resolve_work_start_inputs
from teamctx.team_semantics import (
    load_team_authority,
    load_team_project_config,
    semantics_notices,
)


def _git(root: Path, *args: str) -> None:
    subprocess.run(["git", "-C", str(root), *args], check=True)


def _init_repo(root: Path) -> None:
    _git(root, "init", "-q", "-b", "main")
    _git(root, "config", "user.email", "t@t")
    _git(root, "config", "user.name", "t")
    (root / "README.md").write_text("base\n", encoding="utf-8")
    _git(root, "add", ".")
    _git(root, "commit", "-qm", "base")
    _git(root, "remote", "add", "origin", "git@github.com:acme/widgets.git")


def _write_config(root: Path, **work_start: object) -> None:
    (root / ".teamctx").mkdir(parents=True, exist_ok=True)
    (root / ".teamctx" / "config.json").write_text(
        json.dumps({"schema_version": "teamctx.project_config.v0", "work_start": work_start}),
        encoding="utf-8",
    )


def _write_config_body(root: Path, body: object) -> None:
    (root / ".teamctx").mkdir(parents=True, exist_ok=True)
    (root / ".teamctx" / "config.json").write_text(
        json.dumps(body),
        encoding="utf-8",
    )


def _write_authority(root: Path, priority: int) -> None:
    (root / ".teamctx").mkdir(parents=True, exist_ok=True)
    (root / ".teamctx" / "authority.json").write_text(
        json.dumps(
            [
                {
                    "subject": "rounding-cap",
                    "source": "confluence:Rounding Policy",
                    "priority": priority,
                    "value": "3",
                    "fresh": True,
                }
            ]
        ),
        encoding="utf-8",
    )


def test_project_config_reads_head_blob_when_working_tree_is_dirty(tmp_path: Path) -> None:
    _init_repo(tmp_path)
    _write_config(tmp_path, repo="acme/widgets", docs_root="docs")
    _git(tmp_path, "add", ".teamctx/config.json")
    _git(tmp_path, "commit", "-qm", "config")
    _write_config(tmp_path, repo="other/repo", docs_root="drafts")

    loaded = load_team_project_config(tmp_path)

    assert loaded.config is not None
    assert loaded.config.work_start is not None
    assert loaded.config.work_start.repo == "acme/widgets"
    assert loaded.config.work_start.docs_root == "docs"
    assert loaded.file.state == "committed_dirty"
    assert semantics_notices(config=loaded.file) == (CONFIG_DIRTY_NOTE,)


def test_project_config_reads_clean_committed_head_blob(tmp_path: Path) -> None:
    _init_repo(tmp_path)
    _write_config(tmp_path, repo="acme/widgets", docs_root="docs")
    _git(tmp_path, "add", ".teamctx/config.json")
    _git(tmp_path, "commit", "-qm", "config")

    loaded = load_team_project_config(tmp_path)

    assert loaded.config is not None
    assert loaded.file.state == "committed_clean"
    assert semantics_notices(config=loaded.file) == ()


def test_deleted_worktree_config_still_uses_committed_head_blob(tmp_path: Path) -> None:
    _init_repo(tmp_path)
    _write_config(tmp_path, repo="acme/widgets", docs_root="docs")
    _git(tmp_path, "add", ".teamctx/config.json")
    _git(tmp_path, "commit", "-qm", "config")
    (tmp_path / ".teamctx" / "config.json").unlink()

    loaded = load_team_project_config(tmp_path)

    assert loaded.config is not None
    assert loaded.config.work_start is not None
    assert loaded.config.work_start.docs_root == "docs"
    assert loaded.file.state == "committed_dirty"


def test_untracked_config_is_refused_and_the_git_repo_is_used(tmp_path: Path) -> None:
    _init_repo(tmp_path)
    _write_config(tmp_path, repo="other/repo", docs_root="drafts")

    loaded = load_team_project_config(tmp_path)
    inputs = resolve_work_start_inputs(paths=("src/app.py",), root=tmp_path)

    assert loaded.config is None
    assert loaded.file.state == "uncommitted_refused"
    assert semantics_notices(config=loaded.file) == (COMMIT_CONFIG_TO_ACTIVATE_LINE,)
    assert inputs.repo == "acme/widgets"
    assert inputs.docs_root is None
    assert inputs.semantics_notices == (COMMIT_CONFIG_TO_ACTIVATE_LINE,)


def test_no_git_or_no_head_config_is_refused_with_activation_line(tmp_path: Path) -> None:
    _write_config(tmp_path, repo="other/repo", docs_root="drafts")

    loaded = load_team_project_config(tmp_path)

    assert loaded.config is None
    assert loaded.file.state == "no_git_or_no_head_refused"
    assert semantics_notices(config=loaded.file) == (COMMIT_CONFIG_TO_ACTIVATE_LINE,)


def test_allow_dirty_reads_working_tree_config_with_banner(tmp_path: Path) -> None:
    _init_repo(tmp_path)
    _write_config(tmp_path, repo="acme/widgets", docs_root="docs")
    _git(tmp_path, "add", ".teamctx/config.json")
    _git(tmp_path, "commit", "-qm", "config")
    _write_config(tmp_path, repo="acme/widgets", docs_root="drafts")

    loaded = load_team_project_config(tmp_path, allow_dirty=True)
    inputs = resolve_work_start_inputs(
        paths=("src/app.py",), root=tmp_path, allow_dirty=True
    )

    assert loaded.file.state == "allow_dirty"
    assert loaded.config is not None
    assert loaded.config.work_start is not None
    assert loaded.config.work_start.docs_root == "drafts"
    assert inputs.docs_root == "drafts"
    assert inputs.semantics_notices[0].startswith("using working-tree team config")


def test_resolve_inputs_carries_committed_checks_selection(tmp_path: Path) -> None:
    _init_repo(tmp_path)
    _write_config_body(
        tmp_path,
        {
            "schema_version": "teamctx.project_config.v0",
            "work_start": {"repo": "acme/widgets"},
            "checks": {
                "conflict": {"enabled": True},
                "gate": {"enabled": True, "lane": "fyi"},
                "docs": {"enabled": False},
            },
        },
    )
    _git(tmp_path, "add", ".teamctx/config.json")
    _git(tmp_path, "commit", "-qm", "config")

    inputs = resolve_work_start_inputs(paths=("src/app.py",), root=tmp_path)

    assert inputs.enabled_checks == ("conflict", "gate")
    assert inputs.disabled_checks == ("criteria", "docs")
    assert inputs.important_checks == ("conflict",)


def test_dirty_authority_reads_head_blob_and_reports_the_dirty_note(tmp_path: Path) -> None:
    _init_repo(tmp_path)
    _write_authority(tmp_path, priority=10)
    _git(tmp_path, "add", ".teamctx/authority.json")
    _git(tmp_path, "commit", "-qm", "authority")
    _write_authority(tmp_path, priority=99)

    loaded = load_team_authority(tmp_path)

    assert loaded.file.state == "committed_dirty"
    assert loaded.declarations[0].priority == 10
    assert semantics_notices(authority=loaded.file) == (CONFIG_DIRTY_NOTE,)


def test_ambient_key_moves_when_only_the_team_semantics_state_changes() -> None:
    base = dict(
        repo="acme/widgets",
        forge="github",
        branch="feature",
        paths=("src/app.py",),
        issues=(),
        since=None,
        docs_root=None,
        profile="reflex",
        token_present=True,
        config_bytes=b'{"same": true}',
        authority_bytes=b"",
        authority_state="committed_clean",
    )

    committed = compute_key(**base, config_state="committed_clean")
    dirty = compute_key(**base, config_state="committed_dirty")

    assert committed != dirty
