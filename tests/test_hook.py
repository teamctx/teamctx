from __future__ import annotations

import contextlib
import json
import socket
import subprocess
from dataclasses import replace
from pathlib import Path

import teamctx.hook as hook
from teamctx.connectors.github import ForgeReviewFetch
from teamctx.resolve import resolve_work_start_inputs


def _init_repo(root: Path, url: str = "git@github.com:acme/widgets.git") -> None:
    subprocess.run(["git", "-C", str(root), "init", "-q"], check=True)
    subprocess.run(["git", "-C", str(root), "config", "user.email", "t@t"], check=True)
    subprocess.run(["git", "-C", str(root), "config", "user.name", "t"], check=True)
    (root / ".gitignore").write_text(".teamctx/ambient/\n", encoding="utf-8")
    (root / "src").mkdir()
    (root / "src" / "app.py").write_text("x\n", encoding="utf-8")
    subprocess.run(["git", "-C", str(root), "add", "."], check=True)
    subprocess.run(["git", "-C", str(root), "commit", "-qm", "init"], check=True)
    subprocess.run(["git", "-C", str(root), "checkout", "-qb", "feature"], check=True)
    subprocess.run(["git", "-C", str(root), "remote", "add", "origin", url], check=True)


def _payload(root: Path, file_path: str = "src/app.py", session_id: str = "sess-1") -> str:
    return json.dumps({
        "hook_event_name": "PreToolUse",
        "tool_name": "Edit",
        "tool_input": {"file_path": file_path},
        "cwd": str(root),
        "session_id": session_id,
    })


def _run(payload: str, monkeypatch, capsys) -> str:
    monkeypatch.setattr("sys.stdin.read", lambda: payload)
    hook.main()
    return capsys.readouterr().out


def _state(monkeypatch, tmp_path: Path) -> Path:
    state = tmp_path / ".teamctx" / "ambient"
    monkeypatch.setenv("TEAMCTX_AMBIENT_STATE", str(state))
    monkeypatch.setenv("TEAMCTX_AMBIENT_INTERVAL_SECONDS", "30")
    monkeypatch.setenv("TEAMCTX_DISABLE_GH_AUTH", "1")
    monkeypatch.delenv("TEAMCTX_HOOK_CACHE", raising=False)
    return state


def _grounding(text: str, digest: str, class_of_answer: str = "GOOD") -> hook.Grounding:
    return hook.Grounding(text=text, content_digest=digest, class_of_answer=class_of_answer)


def test_first_edit_emits_can_verify_without_token(monkeypatch, capsys, tmp_path) -> None:
    _init_repo(tmp_path)
    _state(monkeypatch, tmp_path)
    monkeypatch.delenv("GITHUB_TOKEN", raising=False)
    monkeypatch.delenv("GITHUB_TOKEN_FILE", raising=False)

    out = _run(_payload(tmp_path), monkeypatch, capsys)

    data = json.loads(out)
    ctx = data["hookSpecificOutput"]["additionalContext"]
    assert "GitHub" in ctx and "GITHUB_TOKEN" in ctx
    assert "permissionDecision" not in data["hookSpecificOutput"]


def test_same_session_second_edit_inside_interval_is_silent(monkeypatch, capsys, tmp_path) -> None:
    _init_repo(tmp_path)
    _state(monkeypatch, tmp_path)
    now = iter([1000.0, 1001.0])
    calls: list[str] = []

    def fake_ground(root, rel_file, inputs, token_present, baseline=None):  # type: ignore[no-untyped-def]
        calls.append(rel_file)
        return _grounding("first", "digest-1")

    monkeypatch.setattr(hook, "_now_seconds", lambda: next(now))
    monkeypatch.setattr(hook, "_ground", fake_ground)

    assert json.loads(_run(_payload(tmp_path), monkeypatch, capsys))["hookSpecificOutput"][
        "additionalContext"
    ] == "first"
    assert _run(_payload(tmp_path), monkeypatch, capsys).strip() == ""
    assert calls == ["src/app.py"]


def test_after_expiry_changed_world_speaks_full_answer(monkeypatch, capsys, tmp_path) -> None:
    _init_repo(tmp_path)
    _state(monkeypatch, tmp_path)
    now = iter([1000.0, 1030.0])
    groundings = iter([
        _grounding("first answer", "digest-1"),
        _grounding("second answer", "digest-2"),
    ])

    monkeypatch.setattr(hook, "_now_seconds", lambda: next(now))
    monkeypatch.setattr(hook, "_ground", lambda *args: next(groundings))

    first = _run(_payload(tmp_path), monkeypatch, capsys)
    second = _run(_payload(tmp_path), monkeypatch, capsys)

    assert json.loads(first)["hookSpecificOutput"]["additionalContext"] == "first answer"
    assert json.loads(second)["hookSpecificOutput"]["additionalContext"] == "second answer"


def test_after_expiry_unchanged_world_stays_silent(monkeypatch, capsys, tmp_path) -> None:
    _init_repo(tmp_path)
    _state(monkeypatch, tmp_path)
    now = iter([1000.0, 1030.0])
    calls = 0

    def fake_ground(*args):  # type: ignore[no-untyped-def]
        nonlocal calls
        calls += 1
        return _grounding("same answer", "digest-1")

    monkeypatch.setattr(hook, "_now_seconds", lambda: next(now))
    monkeypatch.setattr(hook, "_ground", fake_ground)

    assert _run(_payload(tmp_path), monkeypatch, capsys).strip()
    assert _run(_payload(tmp_path), monkeypatch, capsys).strip() == ""
    assert calls == 2


def test_gap_baseline_restates_after_max_period(monkeypatch, capsys, tmp_path) -> None:
    _init_repo(tmp_path)
    _state(monkeypatch, tmp_path)
    now = iter([1000.0, 1900.0])
    monkeypatch.setattr(hook, "_now_seconds", lambda: next(now))
    monkeypatch.setattr(
        hook,
        "_ground",
        lambda *args: _grounding("still cannot verify", "gap-digest", "GAP-KNOWN"),
    )

    first = _run(_payload(tmp_path), monkeypatch, capsys)
    second = _run(_payload(tmp_path), monkeypatch, capsys)

    assert json.loads(first)["hookSpecificOutput"]["additionalContext"] == "still cannot verify"
    assert json.loads(second)["hookSpecificOutput"]["additionalContext"] == "still cannot verify"


def test_corrupt_state_file_grounds_fresh(monkeypatch, capsys, tmp_path) -> None:
    _init_repo(tmp_path)
    state = _state(monkeypatch, tmp_path)
    state.mkdir(parents=True)
    (state / "sess-1.json").write_text("{not-json", encoding="utf-8")
    monkeypatch.setattr(hook, "_now_seconds", lambda: 1000.0)
    monkeypatch.setattr(hook, "_ground", lambda *args: _grounding("fresh", "digest-1"))

    out = _run(_payload(tmp_path), monkeypatch, capsys)

    assert json.loads(out)["hookSpecificOutput"]["additionalContext"] == "fresh"


def test_recheck_failure_is_silent_and_preserves_good_baseline(
    monkeypatch, capsys, tmp_path
) -> None:
    _init_repo(tmp_path)
    state = _state(monkeypatch, tmp_path)
    now = iter([1000.0, 1030.0])
    groundings = iter([_grounding("first", "digest-1"), SystemExit(1)])

    def fake_ground(*args):  # type: ignore[no-untyped-def]
        value = next(groundings)
        if isinstance(value, BaseException):
            raise value
        return value

    monkeypatch.setattr(hook, "_now_seconds", lambda: next(now))
    monkeypatch.setattr(hook, "_ground", fake_ground)

    assert _run(_payload(tmp_path), monkeypatch, capsys).strip()
    before = (state / "sess-1.json").read_text(encoding="utf-8")
    out = _run(_payload(tmp_path), monkeypatch, capsys)

    assert out.strip() == ""
    assert (state / "sess-1.json").read_text(encoding="utf-8") == before


def test_heads_up_surfaces_a_collision(monkeypatch, capsys, tmp_path) -> None:
    _init_repo(tmp_path)
    _state(monkeypatch, tmp_path)
    import teamctx.connectors.github as gh
    from teamctx.connectors.forge_review import ForgeReviewPullRequest

    monkeypatch.setattr(
        gh,
        "fetch_github_pull_requests",
        lambda **kw: ForgeReviewFetch(
            pull_requests=[ForgeReviewPullRequest(
                provider="github",
                repo="acme/widgets",
                number=7,
                state="open",
                url="https://github.com/acme/widgets/pull/7",
                title=None,
                changed_paths=("src/app.py",),
                created_at="2026-06-27T10:00:00Z",
                updated_at="2026-06-27T11:00:00Z",
            )],
        ),
    )
    monkeypatch.setenv("GITHUB_TOKEN", "t")

    out = _run(_payload(tmp_path), monkeypatch, capsys)

    ctx = json.loads(out)["hookSpecificOutput"]["additionalContext"]
    assert "PR #7" in ctx


def test_non_git_dir_fails_safe(monkeypatch, capsys, tmp_path) -> None:
    _state(monkeypatch, tmp_path)
    payload = json.dumps({
        "hook_event_name": "PreToolUse",
        "tool_name": "Edit",
        "tool_input": {"file_path": "src/app.py"},
        "cwd": str(tmp_path),
        "session_id": "s2",
    })
    out = _run(payload, monkeypatch, capsys)
    assert out.strip() == "" or "permissionDecision" not in json.loads(out)["hookSpecificOutput"]


def test_non_edit_tool_is_noop(monkeypatch, capsys, tmp_path) -> None:
    _state(monkeypatch, tmp_path)
    payload = json.dumps({
        "hook_event_name": "PreToolUse",
        "tool_name": "Bash",
        "tool_input": {"command": "ls"},
        "cwd": str(tmp_path),
        "session_id": "s3",
    })
    out = _run(payload, monkeypatch, capsys)
    assert out.strip() == ""


def test_absolute_file_path_still_matches_collision(monkeypatch, capsys, tmp_path) -> None:
    _init_repo(tmp_path)
    _state(monkeypatch, tmp_path)
    import teamctx.connectors.github as gh
    from teamctx.connectors.forge_review import ForgeReviewPullRequest

    monkeypatch.setattr(gh, "fetch_github_pull_requests", lambda **kw: ForgeReviewFetch(
        pull_requests=[ForgeReviewPullRequest(
            provider="github",
            repo="acme/widgets",
            number=7,
            state="open",
            url="https://github.com/acme/widgets/pull/7",
            title=None,
            changed_paths=("src/app.py",),
            created_at="2026-06-27T10:00:00Z",
            updated_at="2026-06-27T11:00:00Z",
        )],
        unbounded_list=False,
    ))
    monkeypatch.setenv("GITHUB_TOKEN", "t")
    abs_path = str(tmp_path / "src" / "app.py")  # Claude Code passes absolute paths
    payload = _payload(tmp_path, file_path=abs_path, session_id="abs-1")

    out = _run(payload, monkeypatch, capsys)

    ctx = json.loads(out)["hookSpecificOutput"]["additionalContext"]
    assert "PR #7" in ctx
    assert str(tmp_path) not in ctx


def test_network_calls_are_time_bounded(monkeypatch, capsys, tmp_path) -> None:
    _init_repo(tmp_path)
    _state(monkeypatch, tmp_path)
    import teamctx.connectors.github as gh
    import teamctx.work_start as ws

    monkeypatch.setattr(
        gh,
        "fetch_github_pull_requests",
        lambda **kw: ForgeReviewFetch(pull_requests=[]),
    )
    seen: dict[str, object] = {}
    real = ws.ground_work_start

    def spy(*a, **k):  # type: ignore[no-untyped-def]
        seen["timeout"] = socket.getdefaulttimeout()
        return real(*a, **k)

    monkeypatch.setattr(ws, "ground_work_start", spy)
    monkeypatch.setenv("GITHUB_TOKEN", "t")
    before = socket.getdefaulttimeout()
    _run(_payload(tmp_path), monkeypatch, capsys)
    assert seen["timeout"] == 8
    assert socket.getdefaulttimeout() == before


def test_ground_sets_reflex_profile(monkeypatch, tmp_path) -> None:
    _init_repo(tmp_path)
    import teamctx.hook_signal as hs
    import teamctx.work_start as ws

    seen: dict[str, object] = {}

    def fake_ground(inputs, **kwargs):  # type: ignore[no-untyped-def]
        seen["profile"] = inputs.profile
        raise RuntimeError("stop after profile capture")

    monkeypatch.setattr(ws, "ground_work_start", fake_ground)
    monkeypatch.setattr(hs, "hook_signal", lambda *args, **kwargs: "ok")
    monkeypatch.setenv("GITHUB_TOKEN", "t")
    inputs = replace(
        resolve_work_start_inputs(paths=("src/app.py",), token="t", root=tmp_path),
        profile="reflex",
    )

    with contextlib.suppress(RuntimeError):
        hook._ground(tmp_path, "src/app.py", inputs, token_present=True)

    assert seen["profile"] == "reflex"


def test_ground_mints_deltas_when_material_changed_since_the_baseline(
    monkeypatch, tmp_path
) -> None:
    from teamctx.ambient import Baseline, BaselineMaterial, CheckMaterial, FindingMaterial

    _init_repo(tmp_path)
    _state(monkeypatch, tmp_path)
    import teamctx.connectors.github as gh

    # the world now: no open PRs touch the file. The baseline recorded PR #7 as a live collision.
    monkeypatch.setattr(gh, "fetch_github_pull_requests", lambda **kw: ForgeReviewFetch(
        pull_requests=[],
    ))
    monkeypatch.setenv("GITHUB_TOKEN", "t")
    inputs = replace(
        resolve_work_start_inputs(paths=("src/app.py",), token="t", root=tmp_path),
        profile="reflex",
    )
    baseline = Baseline(
        key="k", content_digest="old", class_of_answer="GOOD",
        last_network_check_at=1000.0, last_spoken_at=1000.0,
        material=BaselineMaterial((
            CheckMaterial(
                check="conflict", status="found",
                findings=(FindingMaterial(key="conflict:7", source_display="GitHub PR #7",
                                          paths=("src/app.py",)),),
            ),
        )),
    )

    grounding = hook._ground(tmp_path, "src/app.py", inputs, True, baseline)

    assert grounding.has_deltas is True
    conflict = next(c for c in grounding.material.checks if c.check == "conflict")
    assert conflict.status == "clear"
    assert conflict.findings == ()


def test_first_grounding_has_no_deltas(monkeypatch, tmp_path) -> None:
    _init_repo(tmp_path)
    _state(monkeypatch, tmp_path)
    import teamctx.connectors.github as gh

    monkeypatch.setattr(gh, "fetch_github_pull_requests", lambda **kw: ForgeReviewFetch(
        pull_requests=[],
    ))
    monkeypatch.setenv("GITHUB_TOKEN", "t")
    inputs = replace(
        resolve_work_start_inputs(paths=("src/app.py",), token="t", root=tmp_path),
        profile="reflex",
    )

    grounding = hook._ground(tmp_path, "src/app.py", inputs, True, None)

    assert grounding.has_deltas is False


def test_marker_helpers_are_deleted() -> None:
    assert not hasattr(hook, "_already_grounded")
    assert not hasattr(hook, "_mark_grounded")
    assert not hasattr(hook, "_marker")
