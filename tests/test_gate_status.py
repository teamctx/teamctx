from teamctx.connectors.gate_status import (
    FailingGate,
    normalize_failing_gates,
    unavailable_gates_document,
)
from teamctx.connectors.github_checks import parse_failing_check_runs, run_github_checks_probe
from teamctx.core.contracts import RequestContext


def _request() -> RequestContext:
    return RequestContext(
        schema_version="teamctx.request_context.v0",
        request_id="t",
        repo="teamctx/teamctx",
        branch="build/x",
        task="work",
        paths=["src/teamctx/core/select.py"],
        linked_issues=[],
        requested_at="2026-06-21T00:00:00Z",
        requesting_principal=None,
    )


def test_normalize_emits_missed_gate_signal_with_scope() -> None:
    gate = FailingGate(
        repo="teamctx/teamctx", gate_name="pytest", url="https://gh/run/1",
        files=("src/teamctx/core/select.py",),
    )
    doc = normalize_failing_gates(_request(), [gate], observed_at="2026-06-21T00:00:00Z")
    assert len(doc.source_signals) == 1
    sig = doc.source_signals[0]
    assert sig.signal_type == "missed_gate"
    assert sig.source_family == "ci_deploy"
    assert sig.scope["repo"] == "teamctx/teamctx"
    assert sig.scope["files"] == ["src/teamctx/core/select.py"]
    assert sig.scope["gate"] == "pytest"
    assert sig.scope["url"] == "https://gh/run/1"
    assert sig.id == "sig_missed_gate_pytest_0"
    assert any(s.source_family == "ci_deploy" and s.status == "fresh" for s in doc.source_statuses)


def test_unavailable_gates_document_reports_status_only() -> None:
    doc = unavailable_gates_document(
        _request(), repo="teamctx/teamctx", observed_at="2026-06-21T00:00:00Z",
        safe_user_message="CI status unavailable.",
    )
    assert doc.source_signals == []
    assert doc.source_statuses[0].status == "unavailable"


def test_parse_failing_check_runs_keeps_only_failing() -> None:
    payload = {"check_runs": [
        {"name": "pytest", "status": "completed", "conclusion": "failure", "html_url": "u1"},
        {"name": "ruff", "status": "completed", "conclusion": "success", "html_url": "u2"},
        {"name": "mypy", "status": "in_progress", "conclusion": None, "html_url": "u3"},
    ]}
    failing = parse_failing_check_runs(payload)
    assert failing == [("pytest", "u1")]


def test_probe_uses_injected_opener_and_scopes_to_request_paths() -> None:
    import json

    class _Resp:
        def __init__(self, body: bytes) -> None:
            self._b = body
        def read(self) -> bytes:
            return self._b
        def __enter__(self):  # type: ignore[no-untyped-def]
            return self
        def __exit__(self, *a: object) -> None:
            return None

    def opener(request):  # type: ignore[no-untyped-def]
        body = json.dumps({"check_runs": [
            {"name": "pytest", "status": "completed", "conclusion": "failure", "html_url": "u1"}
        ]}).encode()
        return _Resp(body)

    doc = run_github_checks_probe(
        repo="teamctx/teamctx", ref="build/x", token="t",
        request_context=_request(), observed_at="2026-06-21T00:00:00Z", opener=opener,
    )
    assert len(doc.source_signals) == 1
    sig = doc.source_signals[0]
    assert sig.signal_type == "missed_gate"
    assert sig.scope["files"] == ["src/teamctx/core/select.py"]


def test_probe_without_token_is_unavailable() -> None:
    doc = run_github_checks_probe(
        repo="teamctx/teamctx", ref="build/x", token=None,
        request_context=_request(), observed_at="2026-06-21T00:00:00Z",
    )
    assert doc.source_signals == []
    assert doc.source_statuses[0].status == "unavailable"
