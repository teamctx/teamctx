from __future__ import annotations

import json
import subprocess
from pathlib import Path

import pytest
from click.testing import CliRunner

from teamctx.cli import main
from teamctx.onboard import (
    _LEGACY_SNIPPET_BODY,
    _SNIPPET_END,
    _SNIPPET_HEADING,
    _SNIPPET_START,
    CLAUDE_MD_SNIPPET,
    SnippetState,
    classify_claude_md,
    run_onboard,
    run_status,
)

_OLD_STATUS_STUB_PARTS = ("teamctx is initialized. No sources", " are configured yet.")


@pytest.mark.parametrize(
    ("existing", "state"),
    [
        (
            f"# Project\n\n{_SNIPPET_START}\n{CLAUDE_MD_SNIPPET}{_SNIPPET_END}\n",
            "current",
        ),
        (
            f"{_SNIPPET_START}\n{_LEGACY_SNIPPET_BODY}{_SNIPPET_END}\n",
            "outdated",
        ),
        (
            f"{_SNIPPET_START}\n{_SNIPPET_HEADING}\nI rewrote this.\n{_SNIPPET_END}\n",
            "edited",
        ),
        (
            f"{_SNIPPET_START}\n{CLAUDE_MD_SNIPPET}{_SNIPPET_START}\n{_SNIPPET_END}\n",
            "conflicted_markers",
        ),
        (
            f"# Project\n\n{_LEGACY_SNIPPET_BODY}\n## Other\n",
            "legacy",
        ),
        (
            f"# Project\n\n{_SNIPPET_HEADING}\nMy own setup note.\n",
            "edited_heading",
        ),
        ("# Project\n\nNothing about teamctx here.\n", "absent"),
    ],
)
def test_classify_claude_md_states(existing: str, state: SnippetState) -> None:
    assert classify_claude_md(existing) == state


class _Resp:
    def __init__(self, body: bytes) -> None:
        self._b = body

    def read(self) -> bytes:
        return self._b

    def __enter__(self):  # type: ignore[no-untyped-def]
        return self

    def __exit__(self, *a: object) -> None:
        return None


def _opener_returning(payload: object):  # type: ignore[no-untyped-def]
    return lambda request: _Resp(json.dumps(payload).encode())


def _github_origin(root: Path) -> None:
    subprocess.run(["git", "-C", str(root), "init", "-q"], check=True)
    subprocess.run(
        ["git", "-C", str(root), "remote", "add", "origin", "git@github.com:acme/widgets.git"],
        check=True,
    )


def _gitlab_origin(root: Path) -> None:
    subprocess.run(["git", "-C", str(root), "init", "-q"], check=True)
    subprocess.run(
        [
            "git",
            "-C",
            str(root),
            "remote",
            "add",
            "origin",
            "git@gitlab.com:group/sub/project.git",
        ],
        check=True,
    )


def _step(report_steps, name: str):  # type: ignore[no-untyped-def]
    return next(step for step in report_steps if step.name == name)


def _write_hook_settings(path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps(
            {
                "hooks": {
                    "PreToolUse": [
                        {
                            "matcher": "Edit|Write|MultiEdit",
                            "hooks": [{"type": "command", "command": "teamctx-hook"}],
                        }
                    ]
                }
            }
        ),
        encoding="utf-8",
    )


def test_run_status_empty_non_git_reports_setup_gaps(tmp_path: Path) -> None:
    report = run_status(tmp_path, opener=_opener_returning([]))

    config = _step(report.steps, "config")
    assert config.status == "noted"
    assert "Run `teamctx onboard --repo owner/name`." in config.detail
    assert _step(report.steps, "tracking").detail == "not a git repo; nothing to track."
    assert (
        _step(report.steps, "reachability").detail
        == "no valid repo resolved, so no reachability check was run."
    )
    assert report.next_step == "Run `teamctx onboard` to finish setup."


def test_run_status_reports_hook_from_local_settings(tmp_path: Path) -> None:
    _write_hook_settings(tmp_path / ".claude" / "settings.local.json")

    report = run_status(tmp_path, opener=_opener_returning([]))

    hook = _step(report.steps, "hook")
    assert hook.status == "ok"
    assert "the reflex hook is installed in" in hook.detail
    assert ".claude/settings.local.json" in hook.detail


def test_run_status_committed_hook_reports_move_fix(tmp_path: Path) -> None:
    _write_hook_settings(tmp_path / ".claude" / "settings.json")

    report = run_status(tmp_path, opener=_opener_returning([]))

    hook = _step(report.steps, "hook")
    assert hook.status == "noted"
    assert hook.detail == (
        "the reflex hook is in the committed .claude/settings.json; re-run `teamctx onboard` "
        "to move it to .claude/settings.local.json (a committed hook auto-runs on teammates' "
        "machines)."
    )


def test_run_status_committed_hook_is_not_ok_even_when_local_exists(tmp_path: Path) -> None:
    _write_hook_settings(tmp_path / ".claude" / "settings.local.json")
    _write_hook_settings(tmp_path / ".claude" / "settings.json")

    report = run_status(tmp_path, opener=_opener_returning([]))

    hook = _step(report.steps, "hook")
    assert hook.status == "noted"
    assert "committed .claude/settings.json" in hook.detail


def test_run_status_missing_hook_names_local_settings(tmp_path: Path) -> None:
    report = run_status(tmp_path, opener=_opener_returning([]))

    hook = _step(report.steps, "hook")
    assert hook.status == "noted"
    assert ".claude/settings.local.json" in hook.detail
    assert ".claude/settings.json" not in hook.detail


def test_run_status_after_onboard_reports_read_only_twin(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    _github_origin(tmp_path)
    monkeypatch.setenv("GITHUB_TOKEN", "x")
    opener = _opener_returning([])

    onboard = run_onboard(
        tmp_path, repo_override=None, force=False, dry_run=False, opener=opener
    )
    before = {
        path.relative_to(tmp_path): path.read_text(encoding="utf-8")
        for path in tmp_path.rglob("*")
        if path.is_file() and ".git" not in path.parts
    }
    report = run_status(tmp_path, opener=opener)
    after = {
        path.relative_to(tmp_path): path.read_text(encoding="utf-8")
        for path in tmp_path.rglob("*")
        if path.is_file() and ".git" not in path.parts
    }

    assert before == after
    assert _step(report.steps, "config").status == "ok"
    assert "configures acme/widgets" in _step(report.steps, "config").detail
    assert _step(report.steps, "tracking").status == "ok"
    assert _step(report.steps, "hook").status == "ok"
    assert _step(report.steps, "claude_md").status == "ok"
    assert _step(report.steps, "credential").status == "ok"
    assert _step(report.steps, "reachability").status == "noted"
    assert _step(report.steps, "reachability").detail == _step(onboard.steps, "health").detail
    assert (
        report.next_step
        == (
            "You're set. Team context appears by itself: before your first edit, and again "
            "whenever something changes while you work."
        )
    )


def test_run_status_gitlab_after_onboard_reports_read_only_twin(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    _gitlab_origin(tmp_path)
    monkeypatch.setenv("GITLAB_TOKEN", "x")
    opener = _opener_returning([])

    onboard = run_onboard(
        tmp_path, repo_override=None, force=False, dry_run=False, opener=opener
    )
    before = {
        path.relative_to(tmp_path): path.read_text(encoding="utf-8")
        for path in tmp_path.rglob("*")
        if path.is_file() and ".git" not in path.parts
    }
    report = run_status(tmp_path, opener=opener)
    after = {
        path.relative_to(tmp_path): path.read_text(encoding="utf-8")
        for path in tmp_path.rglob("*")
        if path.is_file() and ".git" not in path.parts
    }

    assert before == after
    assert _step(report.steps, "config").status == "ok"
    assert "configures group/sub/project" in _step(report.steps, "config").detail
    assert _step(report.steps, "credential").status == "ok"
    assert "GITLAB_TOKEN" in _step(report.steps, "credential").detail
    assert _step(report.steps, "reachability").detail == _step(onboard.steps, "health").detail


def test_run_status_invalid_config_json_names_fix(tmp_path: Path) -> None:
    (tmp_path / ".teamctx").mkdir()
    (tmp_path / ".teamctx" / "config.json").write_text("{ not valid json", encoding="utf-8")

    report = run_status(tmp_path, opener=_opener_returning([]))

    config = _step(report.steps, "config")
    assert config.status == "failed"
    assert "exists but is not valid teamctx config" in config.detail
    assert report.next_step == "Fix the failed line above (or run `teamctx onboard --force`)."


def test_status_cli_scaffolded_repo_reports_config(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    _github_origin(tmp_path)
    run_onboard(
        tmp_path, repo_override=None, force=False, dry_run=False, opener=_opener_returning([])
    )
    monkeypatch.chdir(tmp_path)

    result = CliRunner().invoke(main, ["status"], catch_exceptions=False)

    assert result.exit_code == 0, result.output
    assert "teamctx status for" in result.output
    assert "configures acme/widgets" in result.output
    assert "".join(_OLD_STATUS_STUB_PARTS) not in result.output


def test_status_cli_empty_dir_recommends_onboard(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.chdir(tmp_path)

    result = CliRunner().invoke(main, ["status"], catch_exceptions=False)

    assert result.exit_code == 0, result.output
    assert "Run `teamctx onboard` to finish setup." in result.output
    assert "".join(_OLD_STATUS_STUB_PARTS) not in result.output


def test_status_existing_config_with_docs_dir_names_the_real_fix(tmp_path, monkeypatch) -> None:
    # Round-2 review P1: with an EXISTING config (no docs_root) onboard will not set docs, so
    # status must name the real fix (edit config or --force), never promise plain onboard.
    import json as _json
    import subprocess as _sp

    from teamctx.onboard import run_status

    _sp.run(["git", "-C", str(tmp_path), "init", "-q"], check=True)
    _sp.run(
        ["git", "-C", str(tmp_path), "remote", "add", "origin",
         "git@github.com:acme/widgets.git"],
        check=True,
    )
    (tmp_path / ".teamctx").mkdir()
    (tmp_path / ".teamctx" / "config.json").write_text(_json.dumps(
        {"schema_version": "teamctx.project_config.v0", "work_start": {"repo": "acme/widgets"}}
    ), encoding="utf-8")
    (tmp_path / "docs").mkdir()
    (tmp_path / "docs" / "plan.md").write_text("x", encoding="utf-8")
    report = run_status(tmp_path)
    docs = next(s for s in report.steps if s.name == "docs")
    assert "add work_start.docs_root" in docs.detail
    assert "`teamctx onboard` sets it" not in docs.detail


def test_status_empty_docs_dir_is_reported_truthfully(tmp_path) -> None:
    # Round-2 review P2: an empty docs/ folder must not read "no docs/ folder found".
    from teamctx.onboard import run_status

    (tmp_path / "docs").mkdir()
    report = run_status(tmp_path)
    docs = next(s for s in report.steps if s.name == "docs")
    assert "has no markdown files" in docs.detail


def test_status_malformed_config_with_docs_dir_never_promises_plain_onboard(tmp_path) -> None:
    # Round-3 review P1: a malformed config parses to existing=None, but onboard will not write
    # over it without --force, so the docs line must not promise that plain onboard sets it.
    from teamctx.onboard import run_status

    (tmp_path / ".teamctx").mkdir()
    (tmp_path / ".teamctx" / "config.json").write_text("{not json", encoding="utf-8")
    (tmp_path / "docs").mkdir()
    (tmp_path / "docs" / "plan.md").write_text("x", encoding="utf-8")
    report = run_status(tmp_path)
    docs = next(s for s in report.steps if s.name == "docs")
    assert "`teamctx onboard` sets it" not in docs.detail
    assert "add work_start.docs_root" in docs.detail
