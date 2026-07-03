"""Tests for the connector-runner (foundation Phase 2: unified work-start)."""

from __future__ import annotations

import pytest

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
    assert len(documents) == 4


def test_skipped_connectors_emit_disabled_statuses(monkeypatch) -> None:
    _record_calls(monkeypatch)
    inputs = WorkStartInputs(repo="teamctx/teamctx", paths=("src/x.py",))

    _, documents = run_work_start_connectors(inputs, observed_at=OBSERVED)
    disabled = {
        status.source_id: status
        for document in documents
        for status in document.source_statuses
        if status.status == "disabled"
    }

    assert set(disabled) == {"github_issues", "docs_supersession", "github_check_runs"}
    assert disabled["github_issues"].safe_user_message == (
        "spec changes (no issue could be derived from your branch or commits; name one "
        "with --issue)"
    )
    assert disabled["docs_supersession"].safe_user_message == (
        "docs (no docs root is configured; set work_start.docs_root to enable)"
    )
    assert disabled["github_check_runs"].safe_user_message == (
        "failing checks (couldn't determine your branch; pass --branch or --ref)"
    )
    assert all(status.normal_context_visibility == "warning_when_relevant"
               for status in disabled.values())


def test_branch_enables_gate(monkeypatch) -> None:
    called = _record_calls(monkeypatch)
    inputs = WorkStartInputs(repo="teamctx/teamctx", paths=("src/x.py",), branch="feature")
    run_work_start_connectors(inputs, observed_at=OBSERVED)
    assert called == ["collision", "gate"]


def test_issues_require_since(monkeypatch) -> None:
    called = _record_calls(monkeypatch)
    # issues without since: criteria is NOT run (we have no reference point)
    inputs = WorkStartInputs(repo="teamctx/teamctx", paths=("src/x.py",), issues=("#42",))
    _, documents = run_work_start_connectors(inputs, observed_at=OBSERVED)
    assert "criteria" not in called
    status = _status_for_source(documents, "github_issues")
    assert status.safe_user_message == (
        "spec changes (issue #42 was derived, but the start time couldn't be; pass --since)"
    )


def test_issue_skip_note_includes_cap_note(monkeypatch) -> None:
    _record_calls(monkeypatch)
    inputs = WorkStartInputs(
        repo="teamctx/teamctx",
        paths=("src/x.py",),
        issues=("#3", "#4", "#5", "#6", "#7"),
        derived_issues_capped=True,
    )

    _, documents = run_work_start_connectors(inputs, observed_at=OBSERVED)

    status = _status_for_source(documents, "github_issues")
    assert status.safe_user_message == (
        "spec changes (issue #3, #4, #5, #6, #7 was derived, but the start time couldn't be; "
        "pass --since; capped at 5 issues; pass --issue to name others)"
    )


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


def test_reflex_profile_passes_one_page_collision_budget(monkeypatch) -> None:
    captured: dict[str, object] = {}

    def fake_collision(*, max_pages, request_context, observed_at, **kwargs):  # type: ignore[no-untyped-def]
        captured["max_pages"] = max_pages
        return _empty_doc(request_context)

    monkeypatch.setattr(runner, "run_github_pr_probe", fake_collision)
    inputs = WorkStartInputs(
        repo="teamctx/teamctx",
        paths=("src/x.py",),
        profile="reflex",
    )

    run_work_start_connectors(inputs, observed_at=OBSERVED)

    assert captured["max_pages"] == 1


def test_full_profile_passes_three_page_collision_budget(monkeypatch) -> None:
    captured: dict[str, object] = {}

    def fake_collision(*, max_pages, request_context, observed_at, **kwargs):  # type: ignore[no-untyped-def]
        captured["max_pages"] = max_pages
        return _empty_doc(request_context)

    monkeypatch.setattr(runner, "run_github_pr_probe", fake_collision)
    inputs = WorkStartInputs(repo="teamctx/teamctx", paths=("src/x.py",))

    run_work_start_connectors(inputs, observed_at=OBSERVED)

    assert captured["max_pages"] == 3


def test_request_context_shares_paths_and_issues() -> None:
    inputs = WorkStartInputs(
        repo="teamctx/teamctx", paths=("src/x.py",), issues=("#42",), task="do a thing",
    )
    request = build_request_context(inputs, observed_at=OBSERVED)
    assert request.repo == "teamctx/teamctx"
    assert request.paths == ["src/x.py"]
    assert request.linked_issues == ["#42"]
    assert request.task == "do a thing"


def test_workstartinputs_accepts_valid_github_slug() -> None:
    inputs = WorkStartInputs(repo="owner/name", paths=("a.py",))
    assert inputs.repo == "owner/name"
    assert inputs.forge == "github"


def test_workstartinputs_rejects_non_github_repo() -> None:
    with pytest.raises(ValueError, match="github repo"):
        WorkStartInputs(repo="https://gitlab.com/owner/name", paths=("a.py",))


def test_workstartinputs_normalizes_github_url() -> None:
    # A github.com URL passes validation AND is normalized to owner/name, so the connector
    # never receives a raw URL to interpolate into the api.github.com path.
    inputs = WorkStartInputs(repo="https://github.com/owner/name.git", paths=("a.py",))
    assert inputs.repo == "owner/name"


def test_workstartinputs_accepts_valid_gitlab_slug() -> None:
    inputs = WorkStartInputs(repo="group/sub/project", forge="gitlab", paths=("a.py",))
    assert inputs.repo == "group/sub/project"
    assert inputs.forge == "gitlab"


def test_workstartinputs_normalizes_gitlab_url() -> None:
    inputs = WorkStartInputs(
        repo="https://gitlab.com/group/sub/project.git",
        forge="gitlab",
        paths=("a.py",),
    )
    assert inputs.repo == "group/sub/project"


def test_workstartinputs_validates_repo_under_forge() -> None:
    with pytest.raises(ValueError, match="github repo"):
        WorkStartInputs(repo="group/sub/project", forge="github", paths=("a.py",))


def _status_for_source(documents: list[CoreContractDocument], source_id: str):
    for document in documents:
        for status in document.source_statuses:
            if status.source_id == source_id:
                return status
    raise AssertionError(f"missing status {source_id}")
