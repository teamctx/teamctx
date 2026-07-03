from __future__ import annotations

import json
import subprocess
from pathlib import Path

import teamctx.hook as hook
from teamctx.connectors.github import ForgeReviewFetch


def _init_repo(root: Path, url: str = "git@github.com:acme/widgets.git") -> None:
    subprocess.run(["git", "-C", str(root), "init", "-q"], check=True)
    subprocess.run(["git", "-C", str(root), "config", "user.email", "t@t"], check=True)
    subprocess.run(["git", "-C", str(root), "config", "user.name", "t"], check=True)
    (root / "src").mkdir()
    (root / "src" / "app.py").write_text("x\n", encoding="utf-8")
    subprocess.run(["git", "-C", str(root), "add", "."], check=True)
    subprocess.run(["git", "-C", str(root), "commit", "-qm", "init"], check=True)
    subprocess.run(["git", "-C", str(root), "checkout", "-qb", "feature"], check=True)
    subprocess.run(["git", "-C", str(root), "remote", "add", "origin", url], check=True)


def _payload(root: Path, file_path: str = "src/app.py") -> str:
    return json.dumps({
        "hook_event_name": "PreToolUse", "tool_name": "Edit",
        "tool_input": {"file_path": file_path}, "cwd": str(root), "session_id": "sess-1",
    })


def _run(payload: str, monkeypatch, capsys) -> str:
    monkeypatch.setattr("sys.stdin.read", lambda: payload)
    hook.main()
    return capsys.readouterr().out


def test_first_edit_emits_can_verify_without_token(monkeypatch, capsys, tmp_path) -> None:
    _init_repo(tmp_path)
    monkeypatch.delenv("GITHUB_TOKEN", raising=False)
    monkeypatch.delenv("GITHUB_TOKEN_FILE", raising=False)
    monkeypatch.setenv("TEAMCTX_HOOK_CACHE", str(tmp_path / "cache"))
    out = _run(_payload(tmp_path), monkeypatch, capsys)
    data = json.loads(out)
    ctx = data["hookSpecificOutput"]["additionalContext"]
    assert "GitHub" in ctx and "GITHUB_TOKEN" in ctx
    assert "permissionDecision" not in data["hookSpecificOutput"]


def test_once_per_session(monkeypatch, capsys, tmp_path) -> None:
    _init_repo(tmp_path)
    monkeypatch.delenv("GITHUB_TOKEN", raising=False)
    monkeypatch.setenv("TEAMCTX_HOOK_CACHE", str(tmp_path / "cache"))
    _run(_payload(tmp_path), monkeypatch, capsys)
    out2 = _run(_payload(tmp_path), monkeypatch, capsys)
    assert out2.strip() == ""


def test_heads_up_surfaces_a_collision(monkeypatch, capsys, tmp_path) -> None:
    _init_repo(tmp_path)
    import teamctx.connectors.github as gh
    from teamctx.connectors.forge_review import ForgeReviewPullRequest
    monkeypatch.setattr(
        gh, "fetch_github_pull_requests",
        lambda **kw: ForgeReviewFetch(
            pull_requests=[ForgeReviewPullRequest(
                provider="github", repo="acme/widgets", number=7, state="open",
                url="https://github.com/acme/widgets/pull/7", title=None,
                changed_paths=("src/app.py",), created_at="2026-06-27T10:00:00Z",
                updated_at="2026-06-27T11:00:00Z")],
        ),
    )
    monkeypatch.setenv("GITHUB_TOKEN", "t")
    monkeypatch.setenv("TEAMCTX_HOOK_CACHE", str(tmp_path / "cache"))
    out = _run(_payload(tmp_path), monkeypatch, capsys)
    ctx = json.loads(out)["hookSpecificOutput"]["additionalContext"]
    assert "PR #7" in ctx


def test_non_git_dir_fails_safe(monkeypatch, capsys, tmp_path) -> None:
    monkeypatch.setenv("TEAMCTX_HOOK_CACHE", str(tmp_path / "cache"))
    payload = json.dumps({
        "hook_event_name": "PreToolUse", "tool_name": "Edit",
        "tool_input": {"file_path": "src/app.py"}, "cwd": str(tmp_path), "session_id": "s2",
    })
    out = _run(payload, monkeypatch, capsys)
    assert out.strip() == "" or "permissionDecision" not in json.loads(out)["hookSpecificOutput"]


def test_non_edit_tool_is_noop(monkeypatch, capsys, tmp_path) -> None:
    monkeypatch.setenv("TEAMCTX_HOOK_CACHE", str(tmp_path / "cache"))
    payload = json.dumps({
        "hook_event_name": "PreToolUse", "tool_name": "Bash",
        "tool_input": {"command": "ls"}, "cwd": str(tmp_path), "session_id": "s3",
    })
    out = _run(payload, monkeypatch, capsys)
    assert out.strip() == ""


def test_systemexit_in_ground_is_swallowed(monkeypatch, capsys, tmp_path) -> None:
    _init_repo(tmp_path)
    monkeypatch.setenv("TEAMCTX_HOOK_CACHE", str(tmp_path / "cache"))

    def boom(root, file_path):
        raise SystemExit(1)

    monkeypatch.setattr(hook, "_ground", boom)
    out = _run(_payload(tmp_path), monkeypatch, capsys)  # must not raise / exit the process
    assert out.strip() == ""


def test_absolute_file_path_still_matches_collision(monkeypatch, capsys, tmp_path) -> None:
    _init_repo(tmp_path)
    import teamctx.connectors.github as gh
    from teamctx.connectors.forge_review import ForgeReviewPullRequest
    monkeypatch.setattr(gh, "fetch_github_pull_requests", lambda **kw: ForgeReviewFetch(
        pull_requests=[ForgeReviewPullRequest(
            provider="github", repo="acme/widgets", number=7, state="open",
            url="https://github.com/acme/widgets/pull/7", title=None,
            changed_paths=("src/app.py",), created_at="2026-06-27T10:00:00Z",
            updated_at="2026-06-27T11:00:00Z")],
        unbounded_list=False,
    ))
    monkeypatch.setenv("GITHUB_TOKEN", "t")
    monkeypatch.setenv("TEAMCTX_HOOK_CACHE", str(tmp_path / "cache"))
    abs_path = str(tmp_path / "src" / "app.py")  # Claude Code passes ABSOLUTE paths
    payload = json.dumps({"hook_event_name": "PreToolUse", "tool_name": "Edit",
        "tool_input": {"file_path": abs_path}, "cwd": str(tmp_path), "session_id": "abs-1"})
    out = _run(payload, monkeypatch, capsys)
    ctx = json.loads(out)["hookSpecificOutput"]["additionalContext"]
    assert "PR #7" in ctx  # abs path normalized to repo-relative and matched; no false all-clear
    assert str(tmp_path) not in ctx  # signal shows the relative path, not the ugly absolute one


def test_network_calls_are_time_bounded(monkeypatch, capsys, tmp_path) -> None:
    _init_repo(tmp_path)
    import socket

    import teamctx.connectors.github as gh
    import teamctx.work_start as ws
    monkeypatch.setattr(
        gh, "fetch_github_pull_requests",
        lambda **kw: ForgeReviewFetch(pull_requests=[]),
    )
    seen: dict[str, object] = {}
    real = ws.work_start_answer

    def spy(*a, **k):
        seen["timeout"] = socket.getdefaulttimeout()
        return real(*a, **k)

    monkeypatch.setattr(ws, "work_start_answer", spy)
    monkeypatch.setenv("GITHUB_TOKEN", "t")
    monkeypatch.setenv("TEAMCTX_HOOK_CACHE", str(tmp_path / "cache"))
    before = socket.getdefaulttimeout()
    _run(_payload(tmp_path), monkeypatch, capsys)
    assert seen["timeout"] == 8  # a network budget is applied during grounding
    assert socket.getdefaulttimeout() == before  # restored afterward (no global pollution)
