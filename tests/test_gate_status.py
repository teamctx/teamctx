import json

from teamctx.connectors.gate_status import (
    FailingGate,
    normalize_failing_gates,
    pending_gates_document,
    unavailable_gates_document,
)
from teamctx.connectors.github_checks import (
    parse_failing_check_runs,
    parse_incomplete_check_runs,
    run_github_checks_probe,
)
from teamctx.core.contracts import RequestContext


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
    def opener(request):  # type: ignore[no-untyped-def]
        return _Resp(json.dumps(payload).encode())

    return opener


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


def test_parse_incomplete_check_runs_true_when_in_progress_present() -> None:
    payload = {"check_runs": [
        {"name": "ruff", "status": "completed", "conclusion": "success", "html_url": "u"},
        {"name": "mypy", "status": "in_progress", "conclusion": None, "html_url": "u2"},
    ]}
    assert parse_incomplete_check_runs(payload) is True


def test_parse_incomplete_check_runs_false_when_all_completed() -> None:
    payload = {"check_runs": [
        {"name": "ruff", "status": "completed", "conclusion": "success", "html_url": "u"},
    ]}
    assert parse_incomplete_check_runs(payload) is False


def test_pending_gates_document_is_status_only_pending() -> None:
    doc = pending_gates_document(
        _request(), repo="teamctx/teamctx", observed_at="2026-06-21T00:00:00Z",
        safe_user_message="CI checks are still running; the gate is not confirmed green yet.",
    )
    assert doc.source_signals == []
    assert doc.source_statuses[0].status == "pending"
    assert doc.source_statuses[0].source_family == "ci_deploy"


def test_probe_emits_pending_when_only_in_progress() -> None:
    payload = {"total_count": 1, "check_runs": [
        {"name": "mypy", "status": "in_progress", "conclusion": None, "html_url": "u"},
    ]}
    doc = run_github_checks_probe(
        repo="teamctx/teamctx", ref="build/x", token="t", request_context=_request(),
        observed_at="2026-06-21T00:00:00Z", opener=_opener_returning(payload),
    )
    assert doc.source_signals == []
    assert doc.source_statuses[0].status == "pending"


def test_probe_found_dominates_pending() -> None:
    payload = {"total_count": 2, "check_runs": [
        {"name": "pytest", "status": "completed", "conclusion": "failure", "html_url": "u1"},
        {"name": "mypy", "status": "in_progress", "conclusion": None, "html_url": "u2"},
    ]}
    doc = run_github_checks_probe(
        repo="teamctx/teamctx", ref="build/x", token="t", request_context=_request(),
        observed_at="2026-06-21T00:00:00Z", opener=_opener_returning(payload),
    )
    # a failing run wins: a missed_gate signal plus a fresh status, never pending.
    assert any(sig.signal_type == "missed_gate" for sig in doc.source_signals)
    assert doc.source_statuses[0].status == "fresh"


def test_probe_malformed_check_runs_is_unavailable_not_clear() -> None:
    # check_runs present but not a list is malformed: report unavailable, never a false clear.
    doc = run_github_checks_probe(
        repo="teamctx/teamctx", ref="build/x", token="t", request_context=_request(),
        observed_at="2026-06-21T00:00:00Z", opener=_opener_returning({"check_runs": None}),
    )
    assert doc.source_signals == []
    assert doc.source_statuses[0].status == "unavailable"


def test_probe_non_object_run_element_is_unavailable() -> None:
    # a run that is not an object is malformed; never read it as "no failing checks".
    doc = run_github_checks_probe(
        repo="teamctx/teamctx", ref="build/x", token="t", request_context=_request(),
        observed_at="2026-06-21T00:00:00Z",
        opener=_opener_returning({"total_count": 1, "check_runs": [1]}),
    )
    assert doc.source_signals == []
    assert doc.source_statuses[0].status == "unavailable"


def test_probe_failing_run_missing_url_is_unavailable_not_clear() -> None:
    # a completed FAILING run missing its url must not be silently dropped (a false clear).
    payload = {"total_count": 1, "check_runs": [
        {"name": "pytest", "status": "completed", "conclusion": "failure"}
    ]}
    doc = run_github_checks_probe(
        repo="teamctx/teamctx", ref="build/x", token="t", request_context=_request(),
        observed_at="2026-06-21T00:00:00Z", opener=_opener_returning(payload),
    )
    assert doc.source_signals == []
    assert doc.source_statuses[0].status == "unavailable"


def test_probe_non_int_total_count_is_unavailable() -> None:
    # total_count present but not an int means we cannot trust the coverage; fail closed.
    doc = run_github_checks_probe(
        repo="teamctx/teamctx", ref="build/x", token="t", request_context=_request(),
        observed_at="2026-06-21T00:00:00Z",
        opener=_opener_returning({"total_count": "1", "check_runs": []}),
    )
    assert doc.source_signals == []
    assert doc.source_statuses[0].status == "unavailable"


def test_probe_cancelled_run_is_surfaced_not_clear() -> None:
    # a completed run that is not success-like (cancelled) is NOT green; surface it, never clear.
    payload = {"total_count": 1, "check_runs": [
        {"name": "e2e", "status": "completed", "conclusion": "cancelled", "html_url": "u"}
    ]}
    doc = run_github_checks_probe(
        repo="teamctx/teamctx", ref="build/x", token="t", request_context=_request(),
        observed_at="2026-06-21T00:00:00Z", opener=_opener_returning(payload),
    )
    assert any(sig.signal_type == "missed_gate" for sig in doc.source_signals)


def test_probe_skipped_and_neutral_runs_are_clear() -> None:
    # skipped and neutral are success-like per GitHub; they do not falsify the gate.
    payload = {"total_count": 2, "check_runs": [
        {"name": "lint", "status": "completed", "conclusion": "skipped", "html_url": "u1"},
        {"name": "opt", "status": "completed", "conclusion": "neutral", "html_url": "u2"},
    ]}
    doc = run_github_checks_probe(
        repo="teamctx/teamctx", ref="build/x", token="t", request_context=_request(),
        observed_at="2026-06-21T00:00:00Z", opener=_opener_returning(payload),
    )
    assert doc.source_signals == []
    assert doc.source_statuses[0].status == "fresh"
