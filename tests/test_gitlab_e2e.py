from __future__ import annotations

import json
import os
import subprocess
from email.message import Message
from pathlib import Path
from urllib.request import Request

import teamctx.runner as runner_mod
from teamctx.connectors.gitlab import run_gitlab_mr_probe, run_gitlab_pipeline_probe
from teamctx.contract_render import render_broker_answer
from teamctx.resolve import resolve_work_start_inputs
from teamctx.work_start import work_start_answer

OBSERVED = "2026-07-03T12:00:00Z"
REPO = "group/sub/project"


class _Resp:
    def __init__(self, payload: object, *, headers: dict[str, str] | None = None) -> None:
        self._data = json.dumps(payload).encode()
        self.headers = Message()
        for name, value in (headers or {}).items():
            self.headers[name] = value

    def read(self) -> bytes:
        return self._data

    def __enter__(self) -> _Resp:
        return self

    def __exit__(self, *_: object) -> None:
        pass


class _Opener:
    def __init__(self, *responses: _Resp) -> None:
        self.responses = list(responses)
        self.requests: list[Request] = []

    def __call__(self, request: Request) -> _Resp:
        self.requests.append(request)
        if not self.responses:
            raise AssertionError(f"unexpected request: {request.full_url}")
        return self.responses.pop(0)


def _git(root: Path, *args: str, env: dict[str, str] | None = None) -> str:
    result = subprocess.run(
        ["git", "-C", str(root), *args],
        check=True,
        capture_output=True,
        text=True,
        env={**os.environ, **(env or {})},
    )
    return result.stdout.strip()


def _init_gitlab_repo(root: Path) -> None:
    _git(root, "init", "-q", "-b", "main")
    _git(root, "config", "user.email", "t@t")
    _git(root, "config", "user.name", "t")
    target = root / "src" / "app.py"
    target.parent.mkdir(exist_ok=True)
    target.write_text("base\n", encoding="utf-8")
    _git(root, "add", ".")
    _git(root, "commit", "-qm", "base")
    _git(root, "checkout", "-qb", "feature/x")
    target.write_text("work\n", encoding="utf-8")
    _git(root, "commit", "-am", "work", env={
        "GIT_AUTHOR_DATE": "2026-07-02T10:00:00+00:00",
        "GIT_COMMITTER_DATE": "2026-07-02T10:00:00+00:00",
    })
    _git(root, "remote", "add", "origin", f"git@gitlab.com:{REPO}.git")


def _mr(
    iid: int,
    *,
    branch: str,
    source_project_id: int,
    target_project_id: int = 101,
) -> dict[str, object]:
    return {
        "iid": iid,
        "state": "opened",
        "web_url": f"https://gitlab.com/{REPO}/-/merge_requests/{iid}",
        "created_at": "2026-07-03T00:00:00Z",
        "updated_at": f"2026-07-03T00:{iid:02d}:00Z",
        "source_branch": branch,
        "source_project_id": source_project_id,
        "target_project_id": target_project_id,
    }


def _diff(path: str) -> dict[str, object]:
    return {"old_path": path, "new_path": path}


def _pipeline(status: str) -> dict[str, object]:
    return {
        "id": 77,
        "status": status,
        "web_url": f"https://gitlab.com/{REPO}/-/pipelines/77",
    }


def _stub_gitlab(
    monkeypatch,
    *,
    mr_opener: _Opener,
    pipeline_opener: _Opener,
) -> None:
    def mr_probe(**kwargs):  # type: ignore[no-untyped-def]
        return run_gitlab_mr_probe(opener=mr_opener, **kwargs)

    def pipeline_probe(**kwargs):  # type: ignore[no-untyped-def]
        return run_gitlab_pipeline_probe(opener=pipeline_opener, **kwargs)

    monkeypatch.setattr(runner_mod, "run_gitlab_mr_probe", mr_probe)
    monkeypatch.setattr(runner_mod, "run_gitlab_pipeline_probe", pipeline_probe)


def test_gitlab_e2e_collision_own_mr_and_canceled_pipeline(
    monkeypatch,
    tmp_path: Path,
) -> None:
    _init_gitlab_repo(tmp_path)
    monkeypatch.setenv("GITLAB_TOKEN", "gl-token")
    _stub_gitlab(
        monkeypatch,
        mr_opener=_Opener(
            _Resp([
                _mr(7, branch="feature/other", source_project_id=202),
                _mr(12, branch="feature/x", source_project_id=101),
            ]),
            _Resp([_diff("src/app.py")]),
            _Resp([_diff("src/app.py")]),
        ),
        pipeline_opener=_Opener(_Resp([_pipeline("canceled")]), _Resp([])),
    )

    inputs = resolve_work_start_inputs(paths=("src/app.py",), root=tmp_path)
    answer = work_start_answer(inputs, observed_at=OBSERVED, project_root=tmp_path)
    text = render_broker_answer(answer)

    assert inputs.repo == REPO
    assert inputs.forge == "gitlab"
    assert "Before you start, here is what to handle first:" in text
    assert "Open MR !7 changed src/app.py" in text
    assert "gh pr view" not in text
    assert "FYI: Your own open MR !12 for this branch touches these files" in text
    assert "Check 'pipeline canceled' is failing on this branch" in text
    assert dict(answer.verdicts)["Conflict check"].value == "false"
    assert dict(answer.verdicts)["Gate check"].value == "false"


def test_gitlab_e2e_zero_pipeline_disabled_note(
    monkeypatch,
    tmp_path: Path,
) -> None:
    _init_gitlab_repo(tmp_path)
    monkeypatch.setenv("GITLAB_TOKEN", "gl-token")
    _stub_gitlab(
        monkeypatch,
        mr_opener=_Opener(_Resp([])),
        pipeline_opener=_Opener(_Resp([])),
    )

    inputs = resolve_work_start_inputs(paths=("src/app.py",), root=tmp_path)
    answer = work_start_answer(inputs, observed_at=OBSERVED, project_root=tmp_path)
    text = render_broker_answer(answer)

    assert "no pipeline ran for this branch, so the gate is unverified" in text
    assert dict(answer.verdicts)["Gate check"].value == "unknown"
