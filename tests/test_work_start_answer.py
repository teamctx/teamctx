from __future__ import annotations

from teamctx.connectors.github import ForgeReviewFetch
from teamctx.core.broker import BrokerAnswer
from teamctx.runner import WorkStartInputs
from teamctx.work_start import render_work_start, work_start_answer

OBS = "2026-06-27T00:00:00Z"

_EMPTY_FETCH = ForgeReviewFetch(pull_requests=[], truncated=False)


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
    assert "no open PRs touch your files" in text
