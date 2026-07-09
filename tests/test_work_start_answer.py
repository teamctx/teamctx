from __future__ import annotations

import subprocess
from pathlib import Path

from teamctx.connectors.github import ForgeReviewFetch
from teamctx.core.broker import BrokerAnswer
from teamctx.runner import WorkStartInputs
from teamctx.work_start import render_work_start, work_start_answer

OBS = "2026-06-27T00:00:00Z"
EMPTY_PATH_CONFLICT_NOTE = (
    "no files in scope yet; open pull requests can't be compared until there are paths"
)

_EMPTY_FETCH = ForgeReviewFetch(pull_requests=[])


def _init_repo(root: Path) -> None:
    subprocess.run(["git", "-C", str(root), "init", "-q"], check=True)
    subprocess.run(["git", "-C", str(root), "config", "user.email", "t@t"], check=True)
    subprocess.run(["git", "-C", str(root), "config", "user.name", "t"], check=True)
    (root / "README.md").write_text("base\n", encoding="utf-8")
    subprocess.run(["git", "-C", str(root), "add", "."], check=True)
    subprocess.run(["git", "-C", str(root), "commit", "-qm", "base"], check=True)


def test_work_start_answer_returns_broker_answer(monkeypatch) -> None:
    import teamctx.connectors.github as gh
    monkeypatch.setattr(gh, "fetch_github_pull_requests", lambda **kw: _EMPTY_FETCH)
    monkeypatch.setenv("GITHUB_TOKEN", "t")
    inputs = WorkStartInputs(repo="acme/widgets", paths=("src/x.py",), token="t")
    answer = work_start_answer(inputs, observed_at=OBS)
    assert isinstance(answer, BrokerAnswer)
    labels = [label for label, _ in answer.verdicts]
    assert labels == ["Conflict check", "Criteria check", "Docs check", "Gate check"]


def test_render_work_start_still_renders(monkeypatch) -> None:
    import teamctx.connectors.github as gh
    monkeypatch.setattr(gh, "fetch_github_pull_requests", lambda **kw: _EMPTY_FETCH)
    monkeypatch.setenv("GITHUB_TOKEN", "t")
    inputs = WorkStartInputs(repo="acme/widgets", paths=("src/x.py",), token="t")
    text = render_work_start(inputs, observed_at=OBS)
    # conflict clear (git_hosting fresh, no collisions); other checks not configured
    assert "Looks clear to start." in text
    assert "no other open PRs touch your files" in text


def test_render_work_start_with_empty_paths_reports_conflict_not_applicable() -> None:
    inputs = WorkStartInputs(repo="acme/widgets", paths=())

    text = render_work_start(inputs, observed_at=OBS)

    assert EMPTY_PATH_CONFLICT_NOTE in text
    assert "Not applicable:" in text
    assert "no other open PRs touch your files" not in text
    assert not text.startswith("Looks clear to start.")


def test_work_start_answer_loads_authority_from_project_root(monkeypatch, tmp_path) -> None:
    import json

    import teamctx.connectors.github as gh
    monkeypatch.setattr(gh, "fetch_github_pull_requests", lambda **kw: _EMPTY_FETCH)
    _init_repo(tmp_path)
    (tmp_path / ".teamctx").mkdir()
    (tmp_path / ".teamctx" / "authority.json").write_text(
        json.dumps(
            [{"subject": "rounding-cap", "source": "confluence:Policy", "priority": 10,
              "value": "3", "fresh": True}]
        ),
        encoding="utf-8",
    )
    subprocess.run(["git", "-C", str(tmp_path), "add", ".teamctx/authority.json"], check=True)
    subprocess.run(["git", "-C", str(tmp_path), "commit", "-qm", "authority"], check=True)
    inputs = WorkStartInputs(repo="acme/widgets", paths=("src/x.py",), token="t")
    # cwd is NOT tmp_path: authority must be loaded relative to project_root, not the process cwd.
    answer = work_start_answer(inputs, observed_at=OBS, project_root=tmp_path)
    assert [e.subject for e in answer.selection.authority] == ["rounding-cap"]
