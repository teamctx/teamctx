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
    OnboardResult,
    StepResult,
    _atomic_write,
    ensure_config_trackable,
    run_onboard,
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


def _github_origin(root: Path) -> None:
    _init_repo(root, "git@github.com:acme/widgets.git")


def test_run_onboard_happy_path_writes_everything(tmp_path: Path, monkeypatch) -> None:
    _github_origin(tmp_path)
    monkeypatch.setenv("GITHUB_TOKEN", "x")
    result = run_onboard(
        tmp_path, repo_override=None, force=False, dry_run=False, opener=_opener_returning([])
    )
    assert isinstance(result, OnboardResult)
    assert result.ok is True
    assert (tmp_path / ".teamctx" / "config.json").exists()
    assert (tmp_path / "CLAUDE.md").read_text(encoding="utf-8").count(_START) == 1
    names = {s.name for s in result.steps}
    assert {"config", "gitignore", "auth", "hook", "claude_md", "health"} <= names


def test_run_onboard_dry_run_writes_nothing(tmp_path: Path, monkeypatch) -> None:
    _github_origin(tmp_path)
    monkeypatch.setenv("GITHUB_TOKEN", "x")
    result = run_onboard(
        tmp_path, repo_override=None, force=False, dry_run=True, opener=_opener_returning([])
    )
    assert not (tmp_path / ".teamctx" / "config.json").exists()
    assert not (tmp_path / "CLAUDE.md").exists()
    assert not (tmp_path / ".claude").exists()
    # no write step reports having written anything (skipped, or already-satisfied):
    writes = [s for s in result.steps if s.name in {"config", "gitignore", "claude_md", "hook"}]
    assert all(s.status in {"skipped", "already"} for s in writes)


def test_run_onboard_no_repo_stops_writing_nothing(tmp_path: Path) -> None:
    subprocess.run(["git", "-C", str(tmp_path), "init", "-q"], check=True)  # no origin
    result = run_onboard(
        tmp_path, repo_override=None, force=False, dry_run=False, opener=_opener_returning([])
    )
    assert result.ok is False
    assert not (tmp_path / ".teamctx").exists()
    assert "repo" in result.steps[0].detail.lower()


def test_run_onboard_existing_config_needs_force(tmp_path: Path, monkeypatch) -> None:
    _github_origin(tmp_path)
    monkeypatch.setenv("GITHUB_TOKEN", "x")
    run_onboard(
        tmp_path, repo_override=None, force=False, dry_run=False, opener=_opener_returning([])
    )
    again = run_onboard(
        tmp_path, repo_override=None, force=False, dry_run=False, opener=_opener_returning([])
    )
    config_step = next(s for s in again.steps if s.name == "config")
    assert config_step.status == "already" and "force" in config_step.detail.lower()


def test_run_onboard_failed_step_sets_ok_false(tmp_path: Path, monkeypatch) -> None:
    _github_origin(tmp_path)
    monkeypatch.setenv("GITHUB_TOKEN", "x")
    settings = tmp_path / ".claude" / "settings.json"
    settings.parent.mkdir()
    settings.write_text('{"hooks": "not a dict"}', encoding="utf-8")  # malformed
    result = run_onboard(
        tmp_path, repo_override=None, force=False, dry_run=False, opener=_opener_returning([])
    )
    hook_step = next(s for s in result.steps if s.name == "hook")
    assert hook_step.status == "failed"
    assert result.ok is False  # a failed step flips ok


def test_run_onboard_invalid_repo_override(tmp_path: Path) -> None:
    subprocess.run(["git", "-C", str(tmp_path), "init", "-q"], check=True)
    result = run_onboard(
        tmp_path, repo_override="not-a-repo", force=False, dry_run=False,
        opener=_opener_returning([]),
    )
    assert result.ok is False
    assert "not-a-repo" in result.steps[0].detail


def _capturing_opener(urls: list):  # type: ignore[no-untyped-def]
    def opener(request):  # type: ignore[no-untyped-def]
        urls.append(request.full_url)
        return _Resp(b"[]")

    return opener


def test_run_onboard_existing_config_health_uses_runtime_repo(tmp_path: Path, monkeypatch) -> None:
    # git origin is acme/widgets, but an existing config points at other/project. work-start uses
    # the config (config > git-detect), so onboard's health MUST check other/project, not the
    # git-detected repo. This is the setup/runtime split-brain the whole slice refuses.
    _github_origin(tmp_path)  # origin git@github.com:acme/widgets.git
    (tmp_path / ".teamctx").mkdir()
    (tmp_path / ".teamctx" / "config.json").write_text(
        json.dumps(
            {"schema_version": "teamctx.project_config.v0", "work_start": {"repo": "other/project"}}
        ),
        encoding="utf-8",
    )
    monkeypatch.setenv("GITHUB_TOKEN", "x")
    urls: list[str] = []
    result = run_onboard(
        tmp_path, repo_override=None, force=False, dry_run=False, opener=_capturing_opener(urls)
    )
    config_step = next(s for s in result.steps if s.name == "config")
    assert config_step.status == "already" and "other/project" in config_step.detail
    assert urls and "other/project" in urls[0] and "acme/widgets" not in urls[0]


def test_run_onboard_malformed_config_fails(tmp_path: Path) -> None:
    _github_origin(tmp_path)
    (tmp_path / ".teamctx").mkdir()
    (tmp_path / ".teamctx" / "config.json").write_text("{ not valid json", encoding="utf-8")
    result = run_onboard(
        tmp_path, repo_override=None, force=False, dry_run=False, opener=_opener_returning([])
    )
    config_step = next(s for s in result.steps if s.name == "config")
    assert config_step.status == "failed"
    assert result.ok is False


def test_snippet_start_without_end_untouched(tmp_path: Path) -> None:
    content = "# P\n" + _START + "\nbody\n"
    (tmp_path / "CLAUDE.md").write_text(content, encoding="utf-8")
    step = upsert_claude_md_snippet(tmp_path, dry_run=False)
    assert step.status == "skipped"
    assert (tmp_path / "CLAUDE.md").read_text(encoding="utf-8") == content


def test_snippet_empty_file_appends(tmp_path: Path) -> None:
    (tmp_path / "CLAUDE.md").write_text("", encoding="utf-8")
    step = upsert_claude_md_snippet(tmp_path, dry_run=False)
    assert step.status == "wrote"
    assert (tmp_path / "CLAUDE.md").read_text(encoding="utf-8").count(_START) == 1


def test_snippet_legacy_twice_is_left_alone(tmp_path: Path) -> None:
    content = "# P\n" + _LEGACY_SNIPPET_BODY + "\n" + _LEGACY_SNIPPET_BODY + "\n"
    (tmp_path / "CLAUDE.md").write_text(content, encoding="utf-8")
    step = upsert_claude_md_snippet(tmp_path, dry_run=False)
    assert step.status == "skipped"  # two matches -> not confident -> never guess
    assert (tmp_path / "CLAUDE.md").read_text(encoding="utf-8") == content


def test_snippet_eof_no_newline_appends_cleanly(tmp_path: Path) -> None:
    (tmp_path / "CLAUDE.md").write_text("# Project no newline", encoding="utf-8")
    step = upsert_claude_md_snippet(tmp_path, dry_run=False)
    assert step.status == "wrote"
    text = (tmp_path / "CLAUDE.md").read_text(encoding="utf-8")
    assert "# Project no newline" in text and _START in text


def _write_config(root: Path, repo: str | None) -> None:
    (root / ".teamctx").mkdir(exist_ok=True)
    ws = {"repo": repo} if repo is not None else {}
    body: dict = {"schema_version": "teamctx.project_config.v0"}
    if repo is not None:
        body["work_start"] = ws
    (root / ".teamctx" / "config.json").write_text(json.dumps(body), encoding="utf-8")


def test_run_onboard_url_config_repo_normalized_for_health(tmp_path: Path, monkeypatch) -> None:
    # runtime normalizes a config repo through parse_github_repo; onboard health must target the
    # SAME normalized owner/name, not the raw URL (else a split-brain + a malformed request).
    _github_origin(tmp_path)
    _write_config(tmp_path, "https://github.com/other/project.git")
    monkeypatch.setenv("GITHUB_TOKEN", "x")
    urls: list[str] = []
    run_onboard(
        tmp_path, repo_override=None, force=False, dry_run=False, opener=_capturing_opener(urls)
    )
    assert urls and "repos/other/project/" in urls[0]
    # no raw URL artifacts leaked into the api path (the bug was repos/https%3A//.../project.git):
    assert "project.git" not in urls[0] and "%2F" not in urls[0]


def test_run_onboard_invalid_config_repo_fails(tmp_path: Path) -> None:
    _github_origin(tmp_path)
    _write_config(tmp_path, "not-a-repo")  # runtime would reject this
    result = run_onboard(
        tmp_path, repo_override=None, force=False, dry_run=False, opener=_opener_returning([])
    )
    config_step = next(s for s in result.steps if s.name == "config")
    assert config_step.status == "failed" and "not-a-repo" in config_step.detail
    assert result.ok is False


def test_run_onboard_config_without_repo_falls_back_to_git(tmp_path: Path, monkeypatch) -> None:
    # a valid config with no work_start.repo -> runtime uses git-detect; onboard must too.
    _github_origin(tmp_path)  # git origin acme/widgets
    _write_config(tmp_path, None)
    monkeypatch.setenv("GITHUB_TOKEN", "x")
    urls: list[str] = []
    result = run_onboard(
        tmp_path, repo_override=None, force=False, dry_run=False, opener=_capturing_opener(urls)
    )
    assert urls and "repos/acme/widgets/" in urls[0]
    config_step = next(s for s in result.steps if s.name == "config")
    assert config_step.status == "already" and "acme/widgets" in config_step.detail
