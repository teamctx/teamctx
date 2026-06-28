"""Tests for check-runs truncation honesty: no false clear when total_count > page size.

When the check-runs response contains more items than we fetched (total_count > len), the
gate source status must become stale, which routes to incomplete[stale-dep], making the
all-gates-pass verdict UNKNOWN (not true/clear). A visible failing gate in the fetched page
still fires regardless of truncation.

Mirrors tests/test_github_truncation.py but for the gate (ci_deploy) connector.
"""

from __future__ import annotations

import json
from typing import Any
from urllib.request import Request

from teamctx.connectors.gate_status import normalize_failing_gates
from teamctx.connectors.github_checks import (
    CheckRunsFetch,
    fetch_failing_check_runs,
    run_github_checks_probe,
)
from teamctx.core.broker import broker_answer
from teamctx.core.contracts import RequestContext
from teamctx.core.evaluate import Valuation

OBS = "2026-06-28T00:00:00Z"
REPO = "acme/widgets"
TOKEN = "tok"
REF = "feature/x"


def _request() -> RequestContext:
    return RequestContext(
        schema_version="teamctx.request_context.v0",
        request_id="req-gate-trunc",
        repo=REPO,
        branch=REF,
        task="edit x",
        paths=["src/x.py"],
        linked_issues=[],
        requested_at=OBS,
        requesting_principal=None,
    )


class _FakeResponse:
    def __init__(self, payload: object) -> None:
        self._data = json.dumps(payload).encode()

    def read(self) -> bytes:
        return self._data

    def __enter__(self) -> _FakeResponse:
        return self

    def __exit__(self, *_: object) -> None:
        pass


def _check_run(
    name: str,
    *,
    conclusion: str = "success",
    status: str = "completed",
) -> dict[str, Any]:
    return {
        "name": name,
        "status": status,
        "conclusion": conclusion,
        "html_url": f"https://github.com/{REPO}/runs/{name}",
    }


def _make_opener(
    *,
    total_count: int,
    check_runs: list[dict[str, Any]],
) -> Any:
    """Return an opener that serves a check-runs response with the given total_count and list."""

    payload = {"total_count": total_count, "check_runs": check_runs}

    def opener(request: Request) -> _FakeResponse:
        return _FakeResponse(payload)

    return opener


# ---------------------------------------------------------------------------
# Test 1: truncated with total_count (exact), no failing run visible
# -> source status stale -> gate verdict UNKNOWN
# ---------------------------------------------------------------------------


def test_truncated_by_total_count_no_failing_gives_stale_and_unknown_gate_verdict() -> None:
    """total_count=150, 100 check-runs returned, all passing.
    Gate source status must be stale; all-gates-pass verdict must be UNKNOWN."""

    runs = [_check_run(f"job_{i}") for i in range(100)]  # all passing
    opener = _make_opener(total_count=150, check_runs=runs)
    request = _request()

    document = run_github_checks_probe(
        repo=REPO,
        ref=REF,
        token=TOKEN,
        request_context=request,
        observed_at=OBS,
        opener=opener,
    )

    # No failing gate signals visible in the fetched page
    assert document.source_signals == []

    # Source status must be stale (truncated) not fresh
    assert len(document.source_statuses) == 1
    assert document.source_statuses[0].status == "stale", (
        f"expected stale, got {document.source_statuses[0].status!r}"
    )

    # End-to-end: gate verdict must be UNKNOWN, not clear (true)
    answer = broker_answer(request, document.source_signals, document.source_statuses)
    gate_verdict = dict(answer.verdicts)["Gate check"]
    assert gate_verdict == Valuation("unknown", "incomplete[stale-dep]"), (
        f"expected UNKNOWN incomplete[stale-dep], got {gate_verdict!r}"
    )


# ---------------------------------------------------------------------------
# Test 2: truncated WITH a visible failing check-run -> failing card still fires
# ---------------------------------------------------------------------------


def test_truncated_with_visible_failing_run_still_emits_gate_signal() -> None:
    """total_count=150, 100 runs returned, one is failing.
    Truncation must not suppress the visible failing gate signal."""

    runs = [_check_run(f"job_{i}") for i in range(99)]  # 99 passing
    runs.append(_check_run("pytest", conclusion="failure"))  # 1 failing
    opener = _make_opener(total_count=150, check_runs=runs)
    request = _request()

    document = run_github_checks_probe(
        repo=REPO,
        ref=REF,
        token=TOKEN,
        request_context=request,
        observed_at=OBS,
        opener=opener,
    )

    # Status is stale (truncated)
    assert document.source_statuses[0].status == "stale"

    # The failing gate signal is still present
    assert len(document.source_signals) == 1
    sig = document.source_signals[0]
    assert sig.signal_type == "missed_gate"
    assert sig.scope["gate"] == "pytest"

    # End-to-end: a visible failing gate falsifies the universal even under truncation
    answer = broker_answer(request, document.source_signals, document.source_statuses)
    gate_verdict = dict(answer.verdicts)["Gate check"]
    assert gate_verdict == Valuation("false"), (
        f"expected FALSE (failing gate found), got {gate_verdict!r}"
    )


# ---------------------------------------------------------------------------
# Test 3: not truncated (total_count == len) -> status fresh -> gate can clear
# ---------------------------------------------------------------------------


def test_not_truncated_gives_fresh_status() -> None:
    """total_count=3 returned, 3 check-runs, all passing.
    Source status must be fresh (gate can assert all-clear)."""

    runs = [_check_run(f"job_{i}") for i in range(3)]
    opener = _make_opener(total_count=3, check_runs=runs)
    request = _request()

    document = run_github_checks_probe(
        repo=REPO,
        ref=REF,
        token=TOKEN,
        request_context=request,
        observed_at=OBS,
        opener=opener,
    )

    assert document.source_signals == []
    assert document.source_statuses[0].status == "fresh"


# ---------------------------------------------------------------------------
# Test 4: fallback truncation (no total_count, len >= 100) -> stale
# ---------------------------------------------------------------------------


def test_fallback_truncation_without_total_count_when_page_full() -> None:
    """Response has no total_count. 100 check-runs returned (full page) -> truncated."""

    runs = [_check_run(f"job_{i}") for i in range(100)]
    # No total_count key at all
    payload = {"check_runs": runs}

    def opener(request: Request) -> _FakeResponse:
        return _FakeResponse(payload)

    request = _request()
    document = run_github_checks_probe(
        repo=REPO,
        ref=REF,
        token=TOKEN,
        request_context=request,
        observed_at=OBS,
        opener=opener,
    )

    assert document.source_statuses[0].status == "stale"


# ---------------------------------------------------------------------------
# Test 5: fallback truncation (no total_count, len < 100) -> fresh
# ---------------------------------------------------------------------------


def test_fallback_no_truncation_without_total_count_when_page_not_full() -> None:
    """Response has no total_count. 3 check-runs returned -> not truncated."""

    runs = [_check_run(f"job_{i}") for i in range(3)]
    payload = {"check_runs": runs}

    def opener(request: Request) -> _FakeResponse:
        return _FakeResponse(payload)

    request = _request()
    document = run_github_checks_probe(
        repo=REPO,
        ref=REF,
        token=TOKEN,
        request_context=request,
        observed_at=OBS,
        opener=opener,
    )

    assert document.source_statuses[0].status == "fresh"


# ---------------------------------------------------------------------------
# Test 6: fetch_failing_check_runs returns CheckRunsFetch
# ---------------------------------------------------------------------------


def test_fetch_failing_check_runs_returns_check_runs_fetch() -> None:
    """fetch_failing_check_runs returns a CheckRunsFetch dataclass."""

    runs = [_check_run(f"job_{i}") for i in range(3)]
    opener = _make_opener(total_count=3, check_runs=runs)

    result = fetch_failing_check_runs(repo=REPO, ref=REF, token=TOKEN, opener=opener)

    assert isinstance(result, CheckRunsFetch)
    assert result.truncated is False
    assert result.failing == []


def test_fetch_failing_check_runs_truncated_returns_true() -> None:
    """fetch_failing_check_runs returns truncated=True when total_count > len."""

    runs = [_check_run(f"job_{i}") for i in range(100)]
    opener = _make_opener(total_count=150, check_runs=runs)

    result = fetch_failing_check_runs(repo=REPO, ref=REF, token=TOKEN, opener=opener)

    assert isinstance(result, CheckRunsFetch)
    assert result.truncated is True
    assert result.failing == []


# ---------------------------------------------------------------------------
# Test 7: normalize_failing_gates coverage_truncated=True -> stale source status
# ---------------------------------------------------------------------------


def test_normalize_failing_gates_with_coverage_truncated_sets_stale_status() -> None:
    """normalize_failing_gates(coverage_truncated=True) sets source status to stale."""

    request = _request()
    doc = normalize_failing_gates(request, [], observed_at=OBS, coverage_truncated=True)

    assert doc.source_statuses[0].status == "stale"


def test_normalize_failing_gates_default_coverage_truncated_stays_fresh() -> None:
    """normalize_failing_gates default (coverage_truncated=False) keeps fresh status."""

    request = _request()
    doc = normalize_failing_gates(request, [], observed_at=OBS)

    assert doc.source_statuses[0].status == "fresh"
