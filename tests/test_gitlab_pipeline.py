from __future__ import annotations

import json
from email.message import Message
from urllib.request import Request

import pytest

from teamctx.connectors.gitlab import run_gitlab_pipeline_probe
from teamctx.core.broker import broker_answer
from teamctx.core.contracts import CoreContractDocument, RequestContext

REPO = "group/sub/project"
TOKEN = "tok"
OBSERVED = "2026-07-03T00:00:00Z"


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


def _request() -> RequestContext:
    return RequestContext(
        schema_version="teamctx.request_context.v0",
        request_id="t",
        repo=REPO,
        branch="feature/x",
        task="work",
        paths=["src/app.py"],
        linked_issues=[],
        requested_at=OBSERVED,
        requesting_principal=None,
    )


def _pipeline(status: str) -> dict[str, object]:
    return {
        "id": 77,
        "status": status,
        "web_url": "https://gitlab.com/group/sub/project/-/pipelines/77",
    }


def _job(name: str, status: str) -> dict[str, object]:
    return {
        "name": name,
        "status": status,
        "web_url": f"https://gitlab.com/group/sub/project/-/jobs/{name}",
    }


def _doc_for_status(status: str, jobs: list[object] | None = None) -> CoreContractDocument:
    responses = [_Resp([_pipeline(status)])]
    if status in {"failed", "canceled"}:
        responses.append(_Resp(jobs or []))
    return run_gitlab_pipeline_probe(
        repo=REPO,
        ref="feature/x",
        token=TOKEN,
        request_context=_request(),
        observed_at=OBSERVED,
        opener=_Opener(*responses),
    )


def _gate_verdict(doc: CoreContractDocument) -> str:
    answer = broker_answer(_request(), doc.source_signals, doc.source_statuses)
    return dict(answer.verdicts)["Gate check"].value


def test_pipeline_probe_fetches_latest_pipeline_for_encoded_ref() -> None:
    opener = _Opener(_Resp([_pipeline("success")]))

    doc = run_gitlab_pipeline_probe(
        repo=REPO,
        ref="feature/x",
        token=TOKEN,
        request_context=_request(),
        observed_at=OBSERVED,
        opener=opener,
    )

    assert opener.requests[0].full_url == (
        "https://gitlab.com/api/v4/projects/group%2Fsub%2Fproject/pipelines"
        "?ref=feature%2Fx&per_page=1&order_by=updated_at&sort=desc"
    )
    assert doc.source_statuses[0].source_id == "gitlab_pipeline_state"
    assert doc.source_statuses[0].status == "fresh"
    assert _gate_verdict(doc) == "true"


def test_pipeline_probe_missing_token_returns_shared_gate_copy() -> None:
    doc = run_gitlab_pipeline_probe(
        repo=REPO,
        ref="feature/x",
        token=None,
        request_context=_request(),
        observed_at=OBSERVED,
    )

    assert doc.source_statuses[0].source_id == "gitlab_pipeline_state"
    assert doc.source_statuses[0].status == "unavailable"
    assert doc.source_statuses[0].safe_user_message == (
        "CI status is unavailable because no token is configured."
    )


def test_zero_pipelines_is_disabled_with_verbatim_note() -> None:
    doc = run_gitlab_pipeline_probe(
        repo=REPO,
        ref="feature/x",
        token=TOKEN,
        request_context=_request(),
        observed_at=OBSERVED,
        opener=_Opener(_Resp([])),
    )

    assert doc.source_statuses[0].status == "disabled"
    assert doc.source_statuses[0].safe_user_message == (
        "no pipeline ran for this branch, so the gate is unverified"
    )
    assert _gate_verdict(doc) != "true"


@pytest.mark.parametrize(
    "status",
    ["running", "pending", "created", "waiting_for_resource", "preparing", "scheduled"],
)
def test_in_progress_pipeline_statuses_are_pending(status: str) -> None:
    doc = _doc_for_status(status)

    assert doc.source_statuses[0].status == "pending"
    assert _gate_verdict(doc) != "true"


def test_failed_pipeline_with_named_failed_job_emits_gate() -> None:
    doc = _doc_for_status("failed", [_job("pytest", "failed")])

    assert doc.source_statuses[0].status == "fresh"
    assert doc.source_signals[0].scope["gate"] == "pytest"
    assert _gate_verdict(doc) == "false"


@pytest.mark.parametrize("status", ["failed", "canceled"])
def test_failed_or_canceled_without_named_job_synthesizes_pipeline_gate(status: str) -> None:
    doc = _doc_for_status(status, [])

    assert doc.source_statuses[0].status == "fresh"
    assert doc.source_signals[0].scope["gate"] == f"pipeline {status}"
    assert doc.source_signals[0].scope["url"] == (
        "https://gitlab.com/group/sub/project/-/pipelines/77"
    )
    assert _gate_verdict(doc) == "false"


@pytest.mark.parametrize("status", ["skipped", "manual", "weird"])
def test_non_green_ambiguous_pipeline_statuses_are_stale(status: str) -> None:
    doc = _doc_for_status(status)

    assert doc.source_signals == []
    assert doc.source_statuses[0].status == "stale"
    assert "could not be confirmed green" in doc.source_statuses[0].safe_user_message
    assert _gate_verdict(doc) != "true"


def test_malformed_pipeline_payload_is_stale() -> None:
    doc = run_gitlab_pipeline_probe(
        repo=REPO,
        ref="feature/x",
        token=TOKEN,
        request_context=_request(),
        observed_at=OBSERVED,
        opener=_Opener(_Resp([{"id": "77", "status": "success"}])),
    )

    assert doc.source_statuses[0].status == "stale"
    assert _gate_verdict(doc) != "true"


@pytest.mark.parametrize(
    "status",
    [
        "running",
        "pending",
        "created",
        "waiting_for_resource",
        "preparing",
        "scheduled",
        "failed",
        "canceled",
        "skipped",
        "manual",
        "weird",
    ],
)
def test_no_non_success_pipeline_status_can_reach_clear_verdict(status: str) -> None:
    doc = _doc_for_status(status)

    assert _gate_verdict(doc) != "true"
