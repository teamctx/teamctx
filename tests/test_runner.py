"""Tests for the connector-runner (foundation Phase 2: unified work-start)."""

from __future__ import annotations

import teamctx.runner as runner
from teamctx.core.contracts import CoreContractDocument, RequestContext
from teamctx.runner import WorkStartInputs, build_request_context, run_work_start_connectors

OBSERVED = "2026-06-25T12:00:00Z"


def _empty_doc(request_context: RequestContext) -> CoreContractDocument:
    return CoreContractDocument(
        schema_version="teamctx.core_contract_document.v0",
        request_context=request_context,
        source_signals=[],
        source_statuses=[],
        source_open_targets=[],
        guidance_records=[],
        session_context_uses=[],
        context_cards=[],
    )


def _record_calls(monkeypatch):
    """Patch every probe to record that it was called and return an empty document."""

    called: list[str] = []

    def fake(name):
        def probe(*, request_context, observed_at, **kwargs):  # type: ignore[no-untyped-def]
            called.append(name)
            return _empty_doc(request_context)

        return probe

    monkeypatch.setattr(runner, "run_github_pr_probe", fake("collision"))
    monkeypatch.setattr(runner, "run_github_checks_probe", fake("gate"))
    monkeypatch.setattr(runner, "run_github_issues_probe", fake("criteria"))
    monkeypatch.setattr(runner, "run_docs_supersession_probe", fake("docs"))
    return called


def test_collision_only_when_no_optional_inputs(monkeypatch) -> None:
    called = _record_calls(monkeypatch)
    inputs = WorkStartInputs(repo="teamctx/teamctx", paths=("src/x.py",))
    _, documents = run_work_start_connectors(inputs, observed_at=OBSERVED)
    assert called == ["collision"]
    assert len(documents) == 1


def test_branch_enables_gate(monkeypatch) -> None:
    called = _record_calls(monkeypatch)
    inputs = WorkStartInputs(repo="teamctx/teamctx", paths=("src/x.py",), branch="feature")
    run_work_start_connectors(inputs, observed_at=OBSERVED)
    assert called == ["collision", "gate"]


def test_issues_require_since(monkeypatch) -> None:
    called = _record_calls(monkeypatch)
    # issues without since: criteria is NOT run (we have no reference point)
    inputs = WorkStartInputs(repo="teamctx/teamctx", paths=("src/x.py",), issues=("#42",))
    run_work_start_connectors(inputs, observed_at=OBSERVED)
    assert "criteria" not in called


def test_issues_with_since_enables_criteria(monkeypatch) -> None:
    called = _record_calls(monkeypatch)
    inputs = WorkStartInputs(
        repo="teamctx/teamctx", paths=("src/x.py",), issues=("#42",), since=OBSERVED,
    )
    run_work_start_connectors(inputs, observed_at=OBSERVED)
    assert "criteria" in called


def test_docs_root_enables_docs(monkeypatch) -> None:
    called = _record_calls(monkeypatch)
    inputs = WorkStartInputs(repo="teamctx/teamctx", paths=("src/x.py",), docs_root="docs")
    run_work_start_connectors(inputs, observed_at=OBSERVED)
    assert "docs" in called


def test_all_connectors_run_when_all_inputs_present(monkeypatch) -> None:
    called = _record_calls(monkeypatch)
    inputs = WorkStartInputs(
        repo="teamctx/teamctx",
        paths=("src/x.py",),
        branch="feature",
        issues=("#42",),
        since=OBSERVED,
        docs_root="docs",
    )
    _, documents = run_work_start_connectors(inputs, observed_at=OBSERVED)
    assert set(called) == {"collision", "gate", "criteria", "docs"}
    assert len(documents) == 4


def test_ref_overrides_branch_for_gate(monkeypatch) -> None:
    captured: dict[str, object] = {}

    def fake_gate(*, ref, request_context, observed_at, **kwargs):  # type: ignore[no-untyped-def]
        captured["ref"] = ref
        return _empty_doc(request_context)

    monkeypatch.setattr(runner, "run_github_pr_probe",
                        lambda **kw: _empty_doc(kw["request_context"]))
    monkeypatch.setattr(runner, "run_github_checks_probe", fake_gate)
    inputs = WorkStartInputs(
        repo="teamctx/teamctx", paths=("src/x.py",), branch="feature", ref="abc123",
    )
    run_work_start_connectors(inputs, observed_at=OBSERVED)
    assert captured["ref"] == "abc123"


def test_request_context_shares_paths_and_issues() -> None:
    inputs = WorkStartInputs(
        repo="teamctx/teamctx", paths=("src/x.py",), issues=("#42",), task="do a thing",
    )
    request = build_request_context(inputs, observed_at=OBSERVED)
    assert request.repo == "teamctx/teamctx"
    assert request.paths == ["src/x.py"]
    assert request.linked_issues == ["#42"]
    assert request.task == "do a thing"
