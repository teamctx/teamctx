from __future__ import annotations

import json
import subprocess
import time
from dataclasses import replace
from pathlib import Path
from typing import Any
from urllib.parse import urlparse
from urllib.request import Request

import pytest

import teamctx.hook as hook
import teamctx.runner as runner
from teamctx.connectors import github as github_prs
from teamctx.connectors import github_checks, github_issues
from teamctx.resolve import resolve_work_start_inputs


def _init_repo(root: Path) -> None:
    subprocess.run(["git", "-C", str(root), "init", "-q", "-b", "main"], check=True)
    subprocess.run(["git", "-C", str(root), "config", "user.email", "t@t"], check=True)
    subprocess.run(["git", "-C", str(root), "config", "user.name", "t"], check=True)
    (root / ".gitignore").write_text(".teamctx/ambient/\n", encoding="utf-8")
    (root / "src").mkdir()
    (root / "src" / "app.py").write_text("x\n", encoding="utf-8")
    subprocess.run(["git", "-C", str(root), "add", "."], check=True)
    subprocess.run(["git", "-C", str(root), "commit", "-qm", "base"], check=True)
    subprocess.run(
        ["git", "-C", str(root), "remote", "add", "origin", "git@github.com:acme/widgets.git"],
        check=True,
    )
    subprocess.run(["git", "-C", str(root), "checkout", "-qb", "feature"], check=True)


def _payload(root: Path, *, session_id: str = "budget-session") -> str:
    return json.dumps({
        "hook_event_name": "PreToolUse",
        "tool_name": "Edit",
        "tool_input": {"file_path": "src/app.py"},
        "cwd": str(root),
        "session_id": session_id,
    })


def _run_hook(
    payload: str, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> str:
    monkeypatch.setattr("sys.stdin.read", lambda: payload)
    hook.main()
    return capsys.readouterr().out


class _Response:
    def __init__(self, payload: object) -> None:
        self._payload = payload

    def read(self) -> bytes:
        return json.dumps(self._payload).encode("utf-8")

    def __enter__(self) -> _Response:
        return self

    def __exit__(self, exc_type: object, exc: object, traceback: object) -> bool:
        return False


class _CountingGitHubOpener:
    def __init__(self) -> None:
        self.calls: list[tuple[str, str]] = []

    def __call__(self, request: Request) -> _Response:
        method = request.get_method()
        url = request.full_url
        self.calls.append((method, url))
        parsed = urlparse(url)
        path = parsed.path

        if method == "POST" and path.endswith("/graphql"):
            return _Response({
                "data": {
                    "repository": {
                        "pullRequests": {
                            "nodes": [],
                            "pageInfo": {"hasNextPage": False, "endCursor": None},
                        }
                    }
                }
            })
        if method == "GET" and path.endswith("/check-runs"):
            return _Response({"total_count": 0, "check_runs": []})
        if method == "GET" and "/issues/" in path and path.endswith("/events"):
            return _Response([])
        if method == "GET" and "/issues/" in path:
            number = path.rstrip("/").rsplit("/", 1)[-1]
            return _Response({
                "number": int(number),
                "updated_at": "2026-07-02T12:00:00Z",
                "state": "open",
                "title": "Budget pin",
                "html_url": f"https://github.com/acme/widgets/issues/{number}",
                "labels": [],
            })
        raise AssertionError(f"unexpected GitHub request: {method} {url}")

    @property
    def summary(self) -> list[str]:
        return [f"{method} {urlparse(url).path}" for method, url in self.calls]


def _install_counting_opener(
    monkeypatch: pytest.MonkeyPatch, opener: _CountingGitHubOpener
) -> None:
    def run_pr_probe(**kwargs: Any):  # type: ignore[no-untyped-def]
        return github_prs.run_github_pr_probe(**kwargs, opener=opener)

    def run_checks_probe(**kwargs: Any):  # type: ignore[no-untyped-def]
        return github_checks.run_github_checks_probe(**kwargs, opener=opener)

    def run_issues_probe(**kwargs: Any):  # type: ignore[no-untyped-def]
        return github_issues.run_github_issues_probe(**kwargs, opener=opener)

    monkeypatch.setattr(runner, "run_github_pr_probe", run_pr_probe)
    monkeypatch.setattr(runner, "run_github_checks_probe", run_checks_probe)
    monkeypatch.setattr(runner, "run_github_issues_probe", run_issues_probe)


def _ambient_env(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    monkeypatch.setenv("TEAMCTX_AMBIENT_STATE", str(tmp_path / ".teamctx" / "ambient"))
    monkeypatch.setenv("TEAMCTX_AMBIENT_INTERVAL_SECONDS", "30")
    monkeypatch.setenv("TEAMCTX_GITHUB_API_ROOT", "https://api.github.test")
    monkeypatch.setenv("TEAMCTX_DISABLE_GH_AUTH", "1")
    monkeypatch.setenv("GITHUB_TOKEN", "budget-token")
    monkeypatch.delenv("GITHUB_TOKEN_FILE", raising=False)
    monkeypatch.delenv("TEAMCTX_HOOK_CACHE", raising=False)


def test_silent_second_edit_inside_interval_is_zero_network_and_fast(
    monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str], tmp_path: Path
) -> None:
    _init_repo(tmp_path)
    _ambient_env(monkeypatch, tmp_path)
    opener = _CountingGitHubOpener()
    _install_counting_opener(monkeypatch, opener)
    now = iter([1000.0, 1001.0])
    monkeypatch.setattr(hook, "_now_seconds", lambda: next(now))

    first = _run_hook(_payload(tmp_path), monkeypatch, capsys)
    before = len(opener.calls)
    started = time.perf_counter()
    second = _run_hook(_payload(tmp_path), monkeypatch, capsys)
    elapsed = time.perf_counter() - started

    assert json.loads(first)["hookSpecificOutput"]["additionalContext"]
    assert second.strip() == ""
    assert len(opener.calls) == before == 2
    assert elapsed < 0.5


def test_reflex_recheck_budget_without_issues_or_docs_is_one_graphql_and_one_checks_get(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    _init_repo(tmp_path)
    _ambient_env(monkeypatch, tmp_path)
    opener = _CountingGitHubOpener()
    _install_counting_opener(monkeypatch, opener)
    inputs = replace(
        resolve_work_start_inputs(paths=("src/app.py",), token="budget-token", root=tmp_path),
        profile="reflex",
    )

    hook._ground(tmp_path, "src/app.py", inputs, token_present=True)

    assert opener.summary == [
        "POST /graphql",
        "GET /repos/acme/widgets/commits/feature/check-runs",
    ]


def test_reflex_recheck_budget_with_changed_github_issues_adds_issue_and_events_gets(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    _init_repo(tmp_path)
    _ambient_env(monkeypatch, tmp_path)
    opener = _CountingGitHubOpener()
    _install_counting_opener(monkeypatch, opener)
    inputs = replace(
        resolve_work_start_inputs(
            paths=("src/app.py",),
            token="budget-token",
            root=tmp_path,
            issues=("#42", "#43"),
            since="2026-07-01T00:00:00Z",
        ),
        profile="reflex",
    )

    hook._ground(tmp_path, "src/app.py", inputs, token_present=True)

    assert opener.summary == [
        "POST /graphql",
        "GET /repos/acme/widgets/commits/feature/check-runs",
        "GET /repos/acme/widgets/issues/42",
        "GET /repos/acme/widgets/issues/42/events",
        "GET /repos/acme/widgets/issues/43",
        "GET /repos/acme/widgets/issues/43/events",
    ]
