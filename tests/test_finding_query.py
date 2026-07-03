"""Tests for finding_query: parse_selector, match_finding, and broker open_targets plumbing."""

from __future__ import annotations

import pytest

from teamctx.connectors._contract import metadata_only_policy, source_status
from teamctx.connectors.forge_review import ForgeReviewPullRequest, normalize_forge_review_prs
from teamctx.core.broker import broker_answer, broker_answer_from_documents
from teamctx.core.contracts import (
    CoreContractDocument,
    RequestContext,
    SourceOpenTarget,
    SourceSignal,
    SourceStatus,
)
from teamctx.finding_query import (
    AmbiguousFinding,
    FindingSelector,
    FindingSelectorError,
    NoFindingMatch,
    match_finding,
    parse_selector,
)

OBSERVED = "2026-06-28T00:00:00Z"
REPO = "acme/widgets"


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _request(
    paths: list[str] | None = None,
    issues: list[str] | None = None,
) -> RequestContext:
    return RequestContext(
        schema_version="teamctx.request_context.v0",
        request_id="t",
        repo=REPO,
        branch="feature",
        task="work",
        paths=paths or ["src/app.py"],
        linked_issues=issues or [],
        requested_at=OBSERVED,
        requesting_principal=None,
    )


def _policy() -> metadata_only_policy:
    return metadata_only_policy("test evidence")


def _fresh(family: str) -> SourceStatus:
    return source_status(
        source_id=f"{family}-probe",
        source_family=family,
        scope={"repo": REPO},
        status="fresh",
        observed_at=OBSERVED,
        safe_user_message="checked",
        visibility="silent",
        policy_reason="status only",
    )


def _collision_signal(pr_number: int, files: list[str]) -> SourceSignal:
    """A collision signal with pr_number in scope, as forge_review.py produces."""
    return SourceSignal(
        schema_version="teamctx.source_signal.v0",
        id=f"sig_github_pr_{pr_number}_collision",
        signal_type="collision",
        source_family="git_hosting",
        scope={
            "repo": REPO,
            "pr_number": pr_number,
            "state": "open",
            "url": f"https://github.com/acme/widgets/pull/{pr_number}",
            "files": files,
        },
        evidence_summary=f"Open PR #{pr_number} changed {files[0]}.",
        source_display=f"GitHub PR #{pr_number}",
        freshness="fresh",
        confidence="high",
        visibility="visible",
        created_at=OBSERVED,
        observed_at=OBSERVED,
        expires_at="next_refresh",
        policy=metadata_only_policy("pr metadata is evidence"),
    )


def _criteria_signal(issue: str) -> SourceSignal:
    """A criteria-changed signal, as issue_criteria.py produces."""
    return SourceSignal(
        schema_version="teamctx.source_signal.v0",
        id=f"sig_issue_{issue.lstrip('#')}_0",
        signal_type="criteria_changed",
        source_family="issue_tracker",
        scope={
            "repo": REPO,
            "issue": issue,
            "url": f"https://github.com/acme/widgets/issues/{issue.lstrip('#')}",
            "state": "open",
            "change_kinds": ["body_edited"],
        },
        evidence_summary=f"Issue {issue} acceptance criteria changed.",
        source_display=f"GitHub Issue {issue}",
        freshness="fresh",
        confidence="high",
        visibility="visible",
        created_at=OBSERVED,
        observed_at=OBSERVED,
        expires_at="next_refresh",
        policy=metadata_only_policy("issue metadata is evidence"),
    )


def _gate_signal(gate_name: str, files: list[str]) -> SourceSignal:
    """A missed-gate signal, as gate_status.py produces."""
    return SourceSignal(
        schema_version="teamctx.source_signal.v0",
        id=f"sig_missed_gate_{gate_name.replace('-', '_')}_0",
        signal_type="missed_gate",
        source_family="ci_deploy",
        scope={
            "repo": REPO,
            "gate": gate_name,
            "url": "https://github.com/acme/widgets/actions/runs/1",
            "files": files,
        },
        evidence_summary=f"Check '{gate_name}' is failing on this branch.",
        source_display=f"CI: {gate_name}",
        freshness="fresh",
        confidence="high",
        visibility="visible",
        created_at=OBSERVED,
        observed_at=OBSERVED,
        expires_at="next_refresh",
        policy=metadata_only_policy("ci gate status is evidence"),
    )


def _doc_signal(doc: str, superseded_by: str) -> SourceSignal:
    """A doc-superseded signal, as docs_supersession.py produces."""
    return SourceSignal(
        schema_version="teamctx.source_signal.v0",
        id=f"sig_doc_superseded_{doc.replace('/', '_')}",
        signal_type="doc_superseded",
        source_family="docs",
        scope={
            "repo": REPO,
            "doc": doc,
            "superseded_by": superseded_by,
        },
        evidence_summary=f"{doc} was superseded by {superseded_by}.",
        source_display=doc,
        freshness="fresh",
        confidence="high",
        visibility="visible",
        created_at=OBSERVED,
        observed_at=OBSERVED,
        expires_at="next_refresh",
        policy=metadata_only_policy("docs metadata is evidence"),
    )


def _open_target(signal_id: str, index: int = 0) -> SourceOpenTarget:
    return SourceOpenTarget(
        schema_version="teamctx.source_open_target.v0",
        id=f"open_target_{index}",
        source_signal_id=signal_id,
        source_family="git_hosting",
        source_display="GitHub PR #7",
        open_label="Open PR",
        body_availability="status_only",
        policy=metadata_only_policy("open target test"),
    )


def _document_with_open_target(
    request: RequestContext,
    signal: SourceSignal,
    status: SourceStatus,
) -> CoreContractDocument:
    target = _open_target(signal.id)
    return CoreContractDocument(
        schema_version="teamctx.core_contract_document.v0",
        request_context=request,
        source_signals=[signal],
        source_statuses=[status],
        source_open_targets=[target],
        guidance_records=[],
        session_context_uses=[],
        context_cards=[],
    )


# ---------------------------------------------------------------------------
# parse_selector tests
# ---------------------------------------------------------------------------


def test_parse_pr_selector() -> None:
    sel = parse_selector("pr:7")
    assert sel == FindingSelector(kind="pr", value="7")


def test_parse_issue_selector_with_hash() -> None:
    sel = parse_selector("issue:#42")
    assert sel == FindingSelector(kind="issue", value="#42")


def test_parse_issue_selector_without_hash() -> None:
    sel = parse_selector("issue:42")
    assert sel == FindingSelector(kind="issue", value="42")


def test_parse_path_selector() -> None:
    sel = parse_selector("path:src/app.py")
    assert sel == FindingSelector(kind="path", value="src/app.py")


def test_parse_doc_selector() -> None:
    sel = parse_selector("doc:docs/old.md")
    assert sel == FindingSelector(kind="doc", value="docs/old.md")


def test_parse_gate_selector() -> None:
    sel = parse_selector("gate:unit-tests")
    assert sel == FindingSelector(kind="gate", value="unit-tests")


def test_parse_selector_no_colon_raises() -> None:
    with pytest.raises(FindingSelectorError, match="expected one of"):
        parse_selector("pr7")


def test_parse_selector_unknown_kind_raises() -> None:
    with pytest.raises(FindingSelectorError, match="Unknown selector kind"):
        parse_selector("branch:main")


def test_parse_pr_selector_non_numeric_raises() -> None:
    # Fail fast at parse time with a clean message, before any broker run.
    with pytest.raises(FindingSelectorError, match="expects a number"):
        parse_selector("pr:abc")


def test_parse_pr_selector_empty_value_raises() -> None:
    with pytest.raises(FindingSelectorError, match="expects a number"):
        parse_selector("pr:")


def test_parse_pr_selector_numeric_still_works() -> None:
    assert parse_selector("pr:7") == FindingSelector(kind="pr", value="7")


# ---------------------------------------------------------------------------
# match_finding tests: build real BrokerAnswers via broker_answer
# ---------------------------------------------------------------------------


def test_match_pr_selector_finds_collision_card() -> None:
    sig = _collision_signal(pr_number=7, files=["src/app.py"])
    answer = broker_answer(
        _request(paths=["src/app.py"]),
        [sig],
        [_fresh("git_hosting")],
    )
    cards = answer.selection.cards
    card = match_finding(cards, parse_selector("pr:7"))
    assert card.reason_code == "collision.same_path"
    assert card.scope["pr_number"] == 7


def test_match_issue_selector_with_hash() -> None:
    sig = _criteria_signal("#42")
    answer = broker_answer(
        _request(issues=["#42"]),
        [sig],
        [_fresh("issue_tracker")],
    )
    cards = answer.selection.cards
    card = match_finding(cards, parse_selector("issue:#42"))
    assert card.reason_code == "criteria.changed"
    assert card.scope["issue"] == "#42"


def test_match_issue_selector_without_hash_normalizes() -> None:
    sig = _criteria_signal("#42")
    answer = broker_answer(
        _request(issues=["#42"]),
        [sig],
        [_fresh("issue_tracker")],
    )
    cards = answer.selection.cards
    card = match_finding(cards, parse_selector("issue:42"))
    assert card.reason_code == "criteria.changed"


def test_match_issue_selector_matches_jira_keys_case_insensitively_without_hash() -> None:
    sig = _criteria_signal("PROJ-123")
    answer = broker_answer(
        _request(issues=["PROJ-123"]),
        [sig],
        [_fresh("issue_tracker")],
    )
    cards = answer.selection.cards
    card = match_finding(cards, parse_selector("issue:proj-123"))
    assert card.reason_code == "criteria.changed"
    assert card.scope["issue"] == "PROJ-123"


def test_match_gate_selector() -> None:
    sig = _gate_signal("unit-tests", ["src/app.py"])
    answer = broker_answer(
        _request(paths=["src/app.py"]),
        [sig],
        [_fresh("ci_deploy")],
    )
    cards = answer.selection.cards
    card = match_finding(cards, parse_selector("gate:unit-tests"))
    assert card.reason_code == "gate.failed"
    assert card.scope["gate"] == "unit-tests"


def test_match_doc_selector() -> None:
    sig = _doc_signal("docs/old.md", "docs/new.md")
    answer = broker_answer(
        _request(paths=["docs/old.md"]),
        [sig],
        [_fresh("docs")],
    )
    cards = answer.selection.cards
    card = match_finding(cards, parse_selector("doc:docs/old.md"))
    assert card.reason_code == "doc.superseded"
    assert card.scope["doc"] == "docs/old.md"


def test_no_finding_match_raises_with_plain_message() -> None:
    answer = broker_answer(
        _request(paths=["src/app.py"]),
        [],
        [_fresh("git_hosting")],
    )
    cards = answer.selection.cards
    with pytest.raises(NoFindingMatch, match="No current finding matches `pr:99`"):
        match_finding(cards, parse_selector("pr:99"))


def test_no_finding_match_message_mentions_work_start() -> None:
    answer = broker_answer(_request(), [], [_fresh("git_hosting")])
    with pytest.raises(NoFindingMatch, match="work-start"):
        match_finding(answer.selection.cards, parse_selector("pr:99"))


def test_path_selector_matching_two_findings_raises_ambiguous() -> None:
    shared_file = "src/app.py"
    sig_pr = _collision_signal(pr_number=7, files=[shared_file])
    sig_gate = _gate_signal("unit-tests", [shared_file])
    answer = broker_answer(
        _request(paths=[shared_file]),
        [sig_pr, sig_gate],
        [_fresh("git_hosting"), _fresh("ci_deploy")],
    )
    cards = answer.selection.cards
    with pytest.raises(AmbiguousFinding, match="2 findings"):
        match_finding(cards, parse_selector(f"path:{shared_file}"))


def test_ambiguous_finding_message_names_specific_selectors() -> None:
    shared_file = "src/app.py"
    sig_pr = _collision_signal(pr_number=7, files=[shared_file])
    sig_gate = _gate_signal("unit-tests", [shared_file])
    answer = broker_answer(
        _request(paths=[shared_file]),
        [sig_pr, sig_gate],
        [_fresh("git_hosting"), _fresh("ci_deploy")],
    )
    cards = answer.selection.cards
    with pytest.raises(AmbiguousFinding) as exc_info:
        match_finding(cards, parse_selector(f"path:{shared_file}"))
    msg = str(exc_info.value)
    assert "pr:7" in msg
    assert "gate:unit-tests" in msg


# ---------------------------------------------------------------------------
# Part 1a: broker open_targets plumbing test
# ---------------------------------------------------------------------------


def test_broker_answer_from_documents_carries_open_targets() -> None:
    req = _request(paths=["src/app.py"])
    pr = ForgeReviewPullRequest(
        provider="github",
        repo=REPO,
        number=7,
        state="open",
        url="https://github.com/acme/widgets/pull/7",
        title="Add feature",
        changed_paths=("src/app.py",),
        created_at=OBSERVED,
        updated_at=OBSERVED,
    )
    doc = normalize_forge_review_prs(req, [pr], observed_at=OBSERVED)
    assert len(doc.source_open_targets) == 1  # sanity: connector produced one target

    answer = broker_answer_from_documents(req, [doc])
    assert len(answer.open_targets) == 1
    assert answer.open_targets[0].source_signal_id == "sig_github_pr_7_collision"


def test_broker_answer_default_open_targets_empty() -> None:
    answer = broker_answer(
        _request(),
        [],
        [_fresh("git_hosting")],
    )
    assert answer.open_targets == ()


def test_broker_answer_direct_open_targets_param() -> None:
    sig = _collision_signal(pr_number=7, files=["src/app.py"])
    target = _open_target(sig.id)
    answer = broker_answer(
        _request(paths=["src/app.py"]),
        [sig],
        [_fresh("git_hosting")],
        open_targets=[target],
    )
    assert len(answer.open_targets) == 1
    assert answer.open_targets[0] is target
