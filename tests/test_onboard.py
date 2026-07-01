from __future__ import annotations

import json
import os
import subprocess
from pathlib import Path

import pytest

from teamctx.onboard import (
    _LEGACY_SNIPPET_BODY,
    CLAUDE_MD_SNIPPET,
    GithubOnboarder,
    HealthReport,
    StepResult,
    _atomic_write,
    ensure_config_trackable,
    upsert_claude_md_snippet,
)

_START = "<!-- teamctx:start -->"
_END = "<!-- teamctx:end -->"

ROOT = Path(__file__).resolve().parent.parent


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


def _init_repo(root: Path, origin: str) -> None:
    subprocess.run(["git", "-C", str(root), "init", "-q"], check=True)
    subprocess.run(["git", "-C", str(root), "remote", "add", "origin", origin], check=True)


def test_detect_returns_owner_name_for_github_origin(tmp_path: Path) -> None:
    _init_repo(tmp_path, "git@github.com:acme/widgets.git")
    assert GithubOnboarder().detect(tmp_path) == "acme/widgets"


def test_detect_returns_none_for_non_github_origin(tmp_path: Path) -> None:
    _init_repo(tmp_path, "git@gitlab.com:acme/widgets.git")
    assert GithubOnboarder().detect(tmp_path) is None


def test_detect_returns_none_outside_a_repo(tmp_path: Path) -> None:
    assert GithubOnboarder().detect(tmp_path) is None


def test_propose_config_is_repo_fragment() -> None:
    assert GithubOnboarder().propose_config("acme/widgets") == {"repo": "acme/widgets"}


def test_auth_status_reports_found_source(monkeypatch) -> None:
    monkeypatch.setenv("GITHUB_TOKEN", "x")
    status = GithubOnboarder().auth_status()
    assert status.found is True and status.source == "env"
    assert "GITHUB_TOKEN" in status.message


def test_auth_status_reports_missing_with_fix(monkeypatch) -> None:
    monkeypatch.delenv("GITHUB_TOKEN", raising=False)
    monkeypatch.delenv("GITHUB_TOKEN_FILE", raising=False)
    monkeypatch.setenv("TEAMCTX_DISABLE_GH_AUTH", "1")
    status = GithubOnboarder().auth_status()
    assert status.found is False and status.source is None
    assert "GITHUB_TOKEN" in status.message


def test_verify_health_exact_count() -> None:
    report = GithubOnboarder().verify_health(
        "acme/widgets", token="t", opener=_opener_returning([{"number": 1}, {"number": 2}])
    )
    assert isinstance(report, HealthReport)
    assert report.reachable is True
    assert report.open_pr_count == 2 and report.count_is_floor is False
    assert "2 open" in report.message


def test_verify_health_full_page_is_a_floor() -> None:
    report = GithubOnboarder().verify_health(
        "acme/widgets", token="t", opener=_opener_returning([{"number": i} for i in range(100)])
    )
    assert report.count_is_floor is True
    assert "100+" in report.message or "at least 100" in report.message


def test_verify_health_unreachable_is_honest_not_a_verdict() -> None:
    report = GithubOnboarder().verify_health(
        "acme/widgets", token=None, opener=_opener_returning([])
    )
    assert report.reachable is False
    assert "couldn't reach" in report.message.lower() or "no credential" in report.message.lower()


def _git_init(root: Path) -> None:
    subprocess.run(["git", "-C", str(root), "init", "-q"], check=True)


def _is_trackable(root: Path) -> bool:
    return subprocess.run(
        ["git", "-C", str(root), "check-ignore", "--no-index", ".teamctx/config.json"],
        capture_output=True, text=True,
    ).returncode == 1


def test_ensure_trackable_patches_a_blanket_ignore(tmp_path: Path) -> None:
    _git_init(tmp_path)
    (tmp_path / ".gitignore").write_text(".teamctx/\n", encoding="utf-8")  # blanket dir ignore
    step = ensure_config_trackable(tmp_path, dry_run=False)
    assert isinstance(step, StepResult)
    assert step.status == "wrote"
    assert _is_trackable(tmp_path)  # the un-ignore stanza overrides the blanket .teamctx/


def test_ensure_trackable_already_when_nothing_ignores_it(tmp_path: Path) -> None:
    _git_init(tmp_path)  # no .gitignore -> config.json already trackable
    step = ensure_config_trackable(tmp_path, dry_run=False)
    assert step.status == "already"


def test_ensure_trackable_is_idempotent(tmp_path: Path) -> None:
    _git_init(tmp_path)
    (tmp_path / ".gitignore").write_text(".teamctx/\n", encoding="utf-8")
    ensure_config_trackable(tmp_path, dry_run=False)
    body_after_first = (tmp_path / ".gitignore").read_text(encoding="utf-8")
    second = ensure_config_trackable(tmp_path, dry_run=False)
    assert second.status == "already"
    assert (tmp_path / ".gitignore").read_text(encoding="utf-8") == body_after_first  # no dup


def test_ensure_trackable_dry_run_writes_nothing(tmp_path: Path) -> None:
    _git_init(tmp_path)
    (tmp_path / ".gitignore").write_text(".teamctx/\n", encoding="utf-8")
    before = (tmp_path / ".gitignore").read_text(encoding="utf-8")
    step = ensure_config_trackable(tmp_path, dry_run=True)
    assert step.status == "skipped"
    assert (tmp_path / ".gitignore").read_text(encoding="utf-8") == before


def test_snippet_fresh_write_wraps_in_markers(tmp_path: Path) -> None:
    step = upsert_claude_md_snippet(tmp_path, dry_run=False)
    text = (tmp_path / "CLAUDE.md").read_text(encoding="utf-8")
    assert step.status == "wrote"
    assert _START in text and _END in text
    assert "failing checks" in text and "changed specs" not in text


def test_snippet_upsert_is_idempotent(tmp_path: Path) -> None:
    upsert_claude_md_snippet(tmp_path, dry_run=False)
    first = (tmp_path / "CLAUDE.md").read_text(encoding="utf-8")
    step = upsert_claude_md_snippet(tmp_path, dry_run=False)
    assert step.status == "already"
    assert (tmp_path / "CLAUDE.md").read_text(encoding="utf-8") == first
    assert first.count(_START) == 1  # not duplicated


def test_snippet_migrates_unedited_legacy_block(tmp_path: Path) -> None:
    (tmp_path / "CLAUDE.md").write_text(
        "# Project\n\n" + _LEGACY_SNIPPET_BODY + "\n## Other\n", encoding="utf-8"
    )
    step = upsert_claude_md_snippet(tmp_path, dry_run=False)
    text = (tmp_path / "CLAUDE.md").read_text(encoding="utf-8")
    assert step.status == "wrote"
    assert "changed specs" not in text  # legacy body replaced
    assert _START in text and text.count("## Team context (teamctx)") == 1
    assert "## Other" in text  # adjacent content preserved


def test_snippet_warns_not_deletes_edited_legacy_block(tmp_path: Path) -> None:
    edited = "## Team context (teamctx)\nMy own custom teamctx note that I edited.\n"
    (tmp_path / "CLAUDE.md").write_text("# Project\n\n" + edited + "\n## Other\n", encoding="utf-8")
    step = upsert_claude_md_snippet(tmp_path, dry_run=False)
    text = (tmp_path / "CLAUDE.md").read_text(encoding="utf-8")
    assert step.status == "skipped"  # did not touch an edited block
    assert "My own custom teamctx note" in text
    assert "remove" in step.detail.lower()


def test_snippet_malformed_markers_end_before_start_untouched(tmp_path: Path) -> None:
    content = "# P\n" + _END + "\nstuff\n" + _START + "\n"
    (tmp_path / "CLAUDE.md").write_text(content, encoding="utf-8")
    step = upsert_claude_md_snippet(tmp_path, dry_run=False)
    assert step.status == "skipped"
    assert (tmp_path / "CLAUDE.md").read_text(encoding="utf-8") == content  # untouched


def test_snippet_multiple_start_markers_untouched(tmp_path: Path) -> None:
    content = _START + "\na\n" + _END + "\n" + _START + "\nb\n" + _END + "\n"
    (tmp_path / "CLAUDE.md").write_text(content, encoding="utf-8")
    step = upsert_claude_md_snippet(tmp_path, dry_run=False)
    assert step.status == "skipped"
    assert (tmp_path / "CLAUDE.md").read_text(encoding="utf-8") == content


def test_snippet_hand_edited_marked_body_preserved(tmp_path: Path) -> None:
    content = _START + "\n## Team context (teamctx)\nI rewrote this myself.\n" + _END + "\n"
    (tmp_path / "CLAUDE.md").write_text(content, encoding="utf-8")
    step = upsert_claude_md_snippet(tmp_path, dry_run=False)
    assert step.status == "skipped"
    assert "I rewrote this myself." in (tmp_path / "CLAUDE.md").read_text(encoding="utf-8")
