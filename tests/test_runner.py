"""Tests for the connector-runner (foundation Phase 2: unified work-start)."""

from __future__ import annotations

import pytest

import teamctx.runner as runner
from teamctx.connectors.docs_supersession import SupersededDoc, normalize_superseded_docs
from teamctx.connectors.issue_criteria import normalize_issue_changes
from teamctx.core.broker import broker_answer_from_documents
from teamctx.core.contracts import CoreContractDocument, RequestContext
from teamctx.core.evaluate import Valuation
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
    monkeypatch.setattr(runner, "run_jira_issues_probe", fake("jira"))
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


def test_mixed_numeric_and_jira_issues_dispatch_to_both_trackers(monkeypatch) -> None:
    captured: dict[str, object] = {}

    def fake_github_issues(**kwargs):  # type: ignore[no-untyped-def]
        captured["github"] = kwargs
        return _empty_doc(kwargs["request_context"])

    def fake_jira_issues(**kwargs):  # type: ignore[no-untyped-def]
        captured["jira"] = kwargs
        return _empty_doc(kwargs["request_context"])

    monkeypatch.setattr(
        runner,
        "run_github_pr_probe",
        lambda **kw: _empty_doc(kw["request_context"]),
    )
    monkeypatch.setattr(runner, "run_github_issues_probe", fake_github_issues)
    monkeypatch.setattr(runner, "run_jira_issues_probe", fake_jira_issues)
    inputs = WorkStartInputs(
        repo="teamctx/teamctx",
        paths=("src/x.py",),
        token="gh-token",
        issues=("#42", "PROJ-123", "7"),
        since=OBSERVED,
        jira_base_url="https://jira.example.test",
        atlassian_auth=("person@example.com", "atlassian-token"),
    )

    request_context, documents = run_work_start_connectors(inputs, observed_at=OBSERVED)

    assert len(documents) == 5
    assert captured["github"]["issues"] == ["#42", "7"]
    assert captured["github"]["token"] == "gh-token"
    assert captured["jira"]["base_url"] == "https://jira.example.test"
    assert captured["jira"]["issues"] == ["PROJ-123"]
    assert captured["jira"]["auth"] == ("person@example.com", "atlassian-token")
    assert request_context.linked_issues == ["#42", "PROJ-123", "7"]


def test_unconfigured_jira_key_emits_verbatim_disabled_note(monkeypatch) -> None:
    monkeypatch.setattr(
        runner,
        "run_github_pr_probe",
        lambda **kw: _empty_doc(kw["request_context"]),
    )

    def fail_jira(**kwargs):  # type: ignore[no-untyped-def]
        raise AssertionError(f"Jira probe should not run: {kwargs}")

    monkeypatch.setattr(runner, "run_jira_issues_probe", fail_jira)
    inputs = WorkStartInputs(
        repo="teamctx/teamctx",
        paths=("src/x.py",),
        issues=("PROJ-123",),
        since=OBSERVED,
    )

    _, documents = run_work_start_connectors(inputs, observed_at=OBSERVED)

    status = _status_for_source(documents, "jira_issues")
    assert status.status == "disabled"
    assert status.safe_user_message == (
        "issue PROJ-123 looks like a Jira issue, but no Jira is configured; add "
        "work_start.jira to .teamctx/config.json"
    )


def test_mixed_fresh_github_and_unconfigured_jira_stays_stale_dep(monkeypatch) -> None:
    monkeypatch.setattr(
        runner,
        "run_github_pr_probe",
        lambda **kw: _empty_doc(kw["request_context"]),
    )

    def fresh_github_issues(**kwargs):  # type: ignore[no-untyped-def]
        return normalize_issue_changes(
            kwargs["request_context"],
            [],
            observed_at=kwargs["observed_at"],
            source_id="github_issues",
        )

    monkeypatch.setattr(runner, "run_github_issues_probe", fresh_github_issues)
    inputs = WorkStartInputs(
        repo="teamctx/teamctx",
        paths=("src/x.py",),
        issues=("#42", "PROJ-123"),
        since=OBSERVED,
    )

    request_context, documents = run_work_start_connectors(inputs, observed_at=OBSERVED)
    answer = broker_answer_from_documents(request_context, documents)

    verdicts = dict(answer.verdicts)
    assert verdicts["Criteria check"] == Valuation("unknown", "incomplete[stale-dep]")


def test_mixed_fresh_github_and_fresh_jira_criteria_is_complete(monkeypatch) -> None:
    monkeypatch.setattr(
        runner,
        "run_github_pr_probe",
        lambda **kw: _empty_doc(kw["request_context"]),
    )

    def fresh_issues(**kwargs):  # type: ignore[no-untyped-def]
        source_id = "jira_issues" if "base_url" in kwargs else "github_issues"
        return normalize_issue_changes(
            kwargs["request_context"],
            [],
            observed_at=kwargs["observed_at"],
            source_id=source_id,
        )

    monkeypatch.setattr(runner, "run_github_issues_probe", fresh_issues)
    monkeypatch.setattr(runner, "run_jira_issues_probe", fresh_issues)
    inputs = WorkStartInputs(
        repo="teamctx/teamctx",
        paths=("src/x.py",),
        issues=("#42", "PROJ-123"),
        since=OBSERVED,
        jira_base_url="https://jira.example.test",
        atlassian_auth=("person@example.com", "atlassian-token"),
    )

    request_context, documents = run_work_start_connectors(inputs, observed_at=OBSERVED)
    answer = broker_answer_from_documents(request_context, documents)

    verdicts = dict(answer.verdicts)
    assert verdicts["Criteria check"] == Valuation("true")


def test_half_atlassian_credential_emits_verbatim_unavailable_note(monkeypatch) -> None:
    monkeypatch.setattr(
        runner,
        "run_github_pr_probe",
        lambda **kw: _empty_doc(kw["request_context"]),
    )

    def fail_jira(**kwargs):  # type: ignore[no-untyped-def]
        raise AssertionError(f"Jira probe should not run with a half credential: {kwargs}")

    monkeypatch.setattr(runner, "run_jira_issues_probe", fail_jira)
    inputs = WorkStartInputs(
        repo="teamctx/teamctx",
        paths=("src/x.py",),
        issues=("PROJ-123",),
        since=OBSERVED,
        jira_base_url="https://jira.example.test",
        atlassian_auth=None,
        atlassian_auth_missing_half=True,
    )

    _, documents = run_work_start_connectors(inputs, observed_at=OBSERVED)

    status = _status_for_source(documents, "jira_issues")
    assert status.status == "unavailable"
    assert status.safe_user_message == (
        "Jira is configured but only half the Atlassian credential is set; both ATLASSIAN_EMAIL "
        "and ATLASSIAN_API_TOKEN are needed."
    )


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


def test_gitlab_forge_dispatches_to_gitlab_probes_and_never_calls_github(monkeypatch) -> None:
    def fail_github_probe(**kwargs):  # type: ignore[no-untyped-def]
        raise AssertionError(f"GitHub probe should not run: {kwargs}")

    captured: dict[str, object] = {}

    def fake_gitlab_mrs(**kwargs):  # type: ignore[no-untyped-def]
        captured["mrs"] = kwargs
        return _empty_doc(kwargs["request_context"])

    def fake_gitlab_pipeline(**kwargs):  # type: ignore[no-untyped-def]
        captured["pipeline"] = kwargs
        return _empty_doc(kwargs["request_context"])

    monkeypatch.setattr(runner, "run_github_pr_probe", fail_github_probe)
    monkeypatch.setattr(runner, "run_github_checks_probe", fail_github_probe)
    monkeypatch.setattr(runner, "run_github_issues_probe", fail_github_probe)
    monkeypatch.setattr(runner, "run_gitlab_mr_probe", fake_gitlab_mrs)
    monkeypatch.setattr(runner, "run_gitlab_pipeline_probe", fake_gitlab_pipeline)
    monkeypatch.setenv("GITLAB_TOKEN", "gl-token")
    inputs = WorkStartInputs(
        repo="group/sub/project",
        forge="gitlab",
        paths=("src/x.py",),
        branch="feature",
        issues=("#42",),
        since=OBSERVED,
    )

    request_context, documents = run_work_start_connectors(inputs, observed_at=OBSERVED)

    assert len(documents) == 4
    assert request_context.forge == "gitlab"
    assert captured["mrs"]["repo"] == "group/sub/project"
    assert captured["mrs"]["token"] == "gl-token"
    assert captured["mrs"]["max_pages"] == 3
    assert captured["mrs"]["diff_limit"] == 100
    assert captured["pipeline"]["repo"] == "group/sub/project"
    assert captured["pipeline"]["token"] == "gl-token"
    assert captured["pipeline"]["ref"] == "feature"


def test_gitlab_reflex_profile_passes_gitlab_budgets(monkeypatch) -> None:
    captured: dict[str, object] = {}

    def fake_gitlab_mrs(**kwargs):  # type: ignore[no-untyped-def]
        captured["mrs"] = kwargs
        return _empty_doc(kwargs["request_context"])

    def fake_gitlab_pipeline(**kwargs):  # type: ignore[no-untyped-def]
        captured["pipeline"] = kwargs
        return _empty_doc(kwargs["request_context"])

    monkeypatch.setattr(
        runner,
        "run_gitlab_mr_probe",
        fake_gitlab_mrs,
    )
    monkeypatch.setattr(
        runner,
        "run_gitlab_pipeline_probe",
        fake_gitlab_pipeline,
    )
    monkeypatch.setenv("GITLAB_TOKEN", "gl-token")
    inputs = WorkStartInputs(
        repo="group/sub/project",
        forge="gitlab",
        paths=("src/x.py",),
        branch="feature",
        profile="reflex",
    )

    run_work_start_connectors(inputs, observed_at=OBSERVED)

    assert captured["mrs"]["max_pages"] == 1
    assert captured["mrs"]["diff_limit"] == 20


def test_gitlab_without_branch_disables_pipeline_probe(monkeypatch) -> None:
    monkeypatch.setattr(
        runner,
        "run_gitlab_mr_probe",
        lambda **kw: _empty_doc(kw["request_context"]),
    )

    def fail_pipeline(**kwargs):  # type: ignore[no-untyped-def]
        raise AssertionError(f"GitLab pipeline probe should not run: {kwargs}")

    monkeypatch.setattr(runner, "run_gitlab_pipeline_probe", fail_pipeline)
    inputs = WorkStartInputs(repo="group/sub/project", forge="gitlab", paths=("src/x.py",))

    _, documents = run_work_start_connectors(inputs, observed_at=OBSERVED)

    status = _status_for_source(documents, "gitlab_pipeline_state")
    assert status.status == "disabled"
    assert status.safe_user_message == (
        "pipeline state (couldn't determine your branch; pass --branch or --ref)"
    )


def test_request_context_shares_paths_and_issues() -> None:
    inputs = WorkStartInputs(
        repo="teamctx/teamctx", paths=("src/x.py",), issues=("#42",), task="do a thing",
    )
    request = build_request_context(inputs, observed_at=OBSERVED)
    assert request.repo == "teamctx/teamctx"
    assert request.paths == ["src/x.py"]
    assert request.linked_issues == ["#42"]
    assert request.task == "do a thing"
    assert request.forge == "github"


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


def test_confluence_configured_full_profile_runs_probe(monkeypatch) -> None:
    monkeypatch.setattr(
        runner, "run_github_pr_probe", lambda **kw: _empty_doc(kw["request_context"])
    )
    captured: dict[str, object] = {}

    def fake_confluence(**kwargs):  # type: ignore[no-untyped-def]
        captured.update(kwargs)
        return _empty_doc(kwargs["request_context"])

    monkeypatch.setattr(runner, "run_confluence_docs_probe", fake_confluence)
    inputs = WorkStartInputs(
        repo="teamctx/teamctx",
        paths=("src/x.py",),
        confluence_base_url="https://example.atlassian.net",
        confluence_space_key="DEV",
        atlassian_auth=("person@example.com", "atlassian-token"),
    )

    _, documents = run_work_start_connectors(inputs, observed_at=OBSERVED)

    assert captured["base_url"] == "https://example.atlassian.net"
    assert captured["space_key"] == "DEV"
    assert captured["auth"] == ("person@example.com", "atlassian-token")
    # collision + gate-disabled + criteria-disabled + confluence = 4 (NO local-docs disabled
    # entry when Confluence is the configured docs source; it would poison the family)
    assert len(documents) == 4


def test_confluence_reflex_profile_skips_with_verbatim_note(monkeypatch) -> None:
    monkeypatch.setattr(
        runner, "run_github_pr_probe", lambda **kw: _empty_doc(kw["request_context"])
    )

    def fail_confluence(**kwargs):  # type: ignore[no-untyped-def]
        raise AssertionError(f"Confluence probe must not run in reflex profile: {kwargs}")

    monkeypatch.setattr(runner, "run_confluence_docs_probe", fail_confluence)
    inputs = WorkStartInputs(
        repo="teamctx/teamctx",
        paths=("src/x.py",),
        profile="reflex",
        confluence_base_url="https://example.atlassian.net",
        confluence_space_key="DEV",
        atlassian_auth=("person@example.com", "atlassian-token"),
    )

    _, documents = run_work_start_connectors(inputs, observed_at=OBSERVED)

    status = _status_for_source(documents, "confluence_pages")
    assert status.status == "disabled"
    assert status.source_family == "docs"
    assert status.safe_user_message == (
        "Confluence docs are skipped in the quick pre-edit check; run teamctx work-start for "
        "the full scan."
    )


def test_confluence_half_credential_emits_verbatim_note(monkeypatch) -> None:
    monkeypatch.setattr(
        runner, "run_github_pr_probe", lambda **kw: _empty_doc(kw["request_context"])
    )

    def fail_confluence(**kwargs):  # type: ignore[no-untyped-def]
        raise AssertionError(f"Confluence probe must not run with a half credential: {kwargs}")

    monkeypatch.setattr(runner, "run_confluence_docs_probe", fail_confluence)
    inputs = WorkStartInputs(
        repo="teamctx/teamctx",
        paths=("src/x.py",),
        confluence_base_url="https://example.atlassian.net",
        confluence_space_key="DEV",
        atlassian_auth=None,
        atlassian_auth_missing_half=True,
    )

    _, documents = run_work_start_connectors(inputs, observed_at=OBSERVED)

    status = _status_for_source(documents, "confluence_pages")
    assert status.status == "unavailable"
    assert status.safe_user_message == (
        "Confluence is configured but only half the Atlassian credential is set; both "
        "ATLASSIAN_EMAIL and ATLASSIAN_API_TOKEN are needed."
    )


def test_confluence_missing_credential_emits_no_credential_copy(monkeypatch) -> None:
    # No patch of the confluence probe: the real connector returns early on a missing credential
    # (no network) with the verbatim no-credential copy, proving the runner passes auth through.
    monkeypatch.setattr(
        runner, "run_github_pr_probe", lambda **kw: _empty_doc(kw["request_context"])
    )
    inputs = WorkStartInputs(
        repo="teamctx/teamctx",
        paths=("src/x.py",),
        confluence_base_url="https://example.atlassian.net",
        confluence_space_key="DEV",
        atlassian_auth=None,
    )

    _, documents = run_work_start_connectors(inputs, observed_at=OBSERVED)

    status = _status_for_source(documents, "confluence_pages")
    assert status.status == "unavailable"
    assert status.safe_user_message == (
        "Confluence is configured but no Atlassian credential was found. Set ATLASSIAN_EMAIL "
        "and ATLASSIAN_API_TOKEN (or ATLASSIAN_API_TOKEN_FILE)."
    )


def test_confluence_absent_config_adds_no_confluence_document(monkeypatch) -> None:
    _record_calls(monkeypatch)
    inputs = WorkStartInputs(repo="teamctx/teamctx", paths=("src/x.py",))
    _, documents = run_work_start_connectors(inputs, observed_at=OBSERVED)
    source_ids = {s.source_id for d in documents for s in d.source_statuses}
    assert "confluence_pages" not in source_ids


def _request_ctx() -> RequestContext:
    return build_request_context(
        WorkStartInputs(repo="acme/widgets", paths=("src/x.py",)), observed_at=OBSERVED
    )


def _local_docs_fresh(request_context: RequestContext) -> CoreContractDocument:
    return normalize_superseded_docs(
        request_context, [], observed_at=OBSERVED, source_id="docs_supersession"
    )


def test_local_fresh_confluence_stale_docs_family_never_complete_green() -> None:
    # Two docs sources compose under the worst-status rule: local docs fresh but Confluence stale
    # means the docs family can never read complete-green (honest "couldn't fully check").
    request_context = _request_ctx()
    confluence_stale = normalize_superseded_docs(
        request_context,
        [],
        observed_at=OBSERVED,
        source_id="confluence_pages",
        coverage_truncated=True,
        truncated_user_message="A page's supersession marker couldn't be read; the docs scan is "
        "not complete.",
    )
    answer = broker_answer_from_documents(
        request_context, [_local_docs_fresh(request_context), confluence_stale]
    )
    assert dict(answer.verdicts)["Docs check"] == Valuation("unknown", "incomplete[stale-dep]")


def test_local_fresh_confluence_fresh_docs_family_complete() -> None:
    request_context = _request_ctx()
    confluence_fresh = normalize_superseded_docs(
        request_context,
        [
            SupersededDoc(
                repo=request_context.repo,
                doc="Rounding Policy",
                superseded_by="docs/new.md",
                url="https://example.atlassian.net/wiki/spaces/DEV/pages/42/Rounding",
            )
        ],
        observed_at=OBSERVED,
        source_id="confluence_pages",
    )
    answer = broker_answer_from_documents(
        request_context, [_local_docs_fresh(request_context), confluence_fresh]
    )
    # A superseded Confluence page fires the docs card, so the universal is refuted (false), but
    # the family is complete: both docs sources scanned to the end.
    assert dict(answer.verdicts)["Docs check"] == Valuation("false")


def test_confluence_only_docs_config_emits_no_local_disabled_note(monkeypatch) -> None:
    # An unset docs_root beside a configured Confluence space is NOT a coverage gap: the
    # disabled entry would poison the family (disabled+fresh -> stale-dep) and read a clean
    # Confluence scan as unreachable.
    _record_calls(monkeypatch)

    def fake_confluence(*, request_context, observed_at, **kwargs):  # type: ignore[no-untyped-def]
        from teamctx.connectors._contract import source_status
        doc = _empty_doc(request_context)
        doc.source_statuses.append(source_status(
            source_id="confluence_pages", source_family="docs",
            scope={"repo": request_context.repo}, status="fresh", observed_at=observed_at,
            safe_user_message="Docs supersession metadata refreshed.", visibility="silent",
            policy_reason="status only",
        ))
        return doc

    monkeypatch.setattr(runner, "run_confluence_docs_probe", fake_confluence)
    inputs = WorkStartInputs(
        repo="teamctx/teamctx", paths=("src/x.py",),
        confluence_base_url="https://x.example", confluence_space_key="TS",
        atlassian_auth=("e@x", "t"),
    )
    _, documents = run_work_start_connectors(inputs, observed_at=OBSERVED)
    docs_statuses = [
        s for d in documents for s in d.source_statuses if s.source_family == "docs"
    ]
    assert docs_statuses, "the docs family must not be empty when Confluence is configured"
    assert all(s.source_id != "docs_supersession" or s.status != "disabled" for s in docs_statuses)
