from __future__ import annotations

import json
import os
import subprocess
from pathlib import Path

from teamctx.contract_render import render_broker_answer
from teamctx.resolve import resolve_work_start_inputs
from teamctx.work_start import work_start_answer

OBSERVED = "2026-07-03T12:00:00Z"


def _git(root: Path, *args: str, env: dict[str, str] | None = None) -> str:
    result = subprocess.run(
        ["git", "-C", str(root), *args],
        check=True,
        capture_output=True,
        text=True,
        env={**os.environ, **(env or {})},
    )
    return result.stdout.strip()


def _commit(root: Path, message: str, date: str) -> None:
    target = root / "src" / "auth.py"
    target.parent.mkdir(exist_ok=True)
    existing = target.read_text(encoding="utf-8") if target.exists() else ""
    target.write_text(existing + f"{message}\n", encoding="utf-8")
    _git(root, "add", ".")
    env = {"GIT_AUTHOR_DATE": date, "GIT_COMMITTER_DATE": date}
    _git(root, "commit", "-qm", message, env=env)


def _init_repo(root: Path, branch: str) -> None:
    _git(root, "init", "-q", "-b", "main")
    _git(root, "config", "user.email", "t@t")
    _git(root, "config", "user.name", "t")
    _commit(root, "base", "2026-07-01T09:15:00+00:00")
    _git(root, "update-ref", "refs/remotes/origin/main", "HEAD")
    _git(root, "symbolic-ref", "refs/remotes/origin/HEAD", "refs/remotes/origin/main")
    _git(root, "checkout", "-qb", branch)
    _commit(root, "work", "2026-07-02T10:00:00+00:00")


def _fake_issue_opener(updated_at: str):
    class FakeResponse:
        def __init__(self, data: object) -> None:
            self._data = data

        def read(self) -> bytes:
            return json.dumps(self._data).encode()

        def __enter__(self):
            return self

        def __exit__(self, *args):
            pass

    def opener(request):
        url = request.full_url
        if "/issues/42/events" in url:
            return FakeResponse([])
        if "/issues/42" in url:
            return FakeResponse({
                "number": 42,
                "updated_at": updated_at,
                "state": "open",
                "title": "Fix auth",
                "html_url": "https://github.com/acme/widgets/issues/42",
                "labels": [],
            })
        return FakeResponse({})

    return opener


def _stub_github(monkeypatch, issue_opener, captured: dict[str, object]) -> None:
    import teamctx.connectors.github as gh
    import teamctx.connectors.github_checks as gc
    import teamctx.runner as runner_mod
    from teamctx.connectors.github import ForgeReviewFetch
    from teamctx.connectors.github_checks import CheckRunsFetch

    monkeypatch.setattr(
        gh,
        "fetch_github_pull_requests",
        lambda **kw: ForgeReviewFetch(pull_requests=[], truncated=False),
    )
    monkeypatch.setattr(
        gc,
        "fetch_failing_check_runs",
        lambda **kw: CheckRunsFetch(failing=[], truncated=False, pending=False),
    )
    real_issues_probe = runner_mod.run_github_issues_probe

    def issues_probe(**kwargs):
        captured["issues"] = kwargs["issues"]
        captured["since"] = kwargs["since"]
        return real_issues_probe(opener=issue_opener, **kwargs)

    monkeypatch.setattr(runner_mod, "run_github_issues_probe", issues_probe)


def test_auto_derivation_fires_criteria_connector_and_renders_provenance(
    monkeypatch, tmp_path: Path,
) -> None:
    _init_repo(tmp_path, "42-fix-auth")
    captured: dict[str, object] = {}
    _stub_github(monkeypatch, _fake_issue_opener("2026-07-01T09:15:00Z"), captured)

    inputs = resolve_work_start_inputs(
        paths=("src/auth.py",),
        repo="acme/widgets",
        token="t",
        root=tmp_path,
    )
    answer = work_start_answer(inputs, observed_at=OBSERVED, project_root=tmp_path)
    text = render_broker_answer(answer)

    assert captured == {"issues": ["#42"], "since": "2026-07-01T09:15:00Z"}
    assert "the linked issue's criteria are unchanged (issue #42 from your branch name)" in text


def test_auto_derivation_no_issue_renders_precise_not_checked_note(
    monkeypatch, tmp_path: Path,
) -> None:
    _init_repo(tmp_path, "feature")
    captured: dict[str, object] = {}
    _stub_github(monkeypatch, _fake_issue_opener("2026-07-01T09:15:00Z"), captured)

    inputs = resolve_work_start_inputs(
        paths=("src/auth.py",),
        repo="acme/widgets",
        token="t",
        root=tmp_path,
    )
    answer = work_start_answer(inputs, observed_at=OBSERVED, project_root=tmp_path)
    text = render_broker_answer(answer)

    assert captured == {}
    assert (
        "spec changes (no issue could be derived from your branch or commits; name one "
        "with --issue)"
    ) in text
