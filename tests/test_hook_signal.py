from __future__ import annotations

from teamctx.connectors._contract import metadata_only_policy, source_status
from teamctx.core.broker import broker_answer
from teamctx.core.contracts import RequestContext, SourceSignal, SourceStatus
from teamctx.hook_signal import hook_signal


def _request(paths=("src/app.py",)) -> RequestContext:
    return RequestContext(
        schema_version="teamctx.request_context.v0",
        request_id="t",
        repo="acme/widgets",
        branch="feature",
        task="work",
        paths=list(paths),
        linked_issues=[],
        requested_at="2026-06-27T00:00:00Z",
        requesting_principal=None,
    )


def _collision_signal() -> SourceSignal:
    return SourceSignal(
        schema_version="teamctx.source_signal.v0",
        id="sig_pr_7",
        signal_type="collision",
        source_family="git_hosting",
        scope={"repo": "acme/widgets", "files": ["src/app.py"]},
        evidence_summary="PR #7 changes src/app.py",
        source_display="github acme/widgets#7",
        freshness="fresh",
        confidence="high",
        visibility="visible",
        created_at="2026-06-27T00:00:00Z",
        observed_at="2026-06-27T00:00:00Z",
        expires_at="next_refresh",
        policy=metadata_only_policy("pr metadata is evidence"),
    )


def _fresh_status(family: str) -> SourceStatus:
    return source_status(
        source_id=f"{family}-probe",
        source_family=family,
        scope={"repo": "acme/widgets"},
        status="fresh",
        observed_at="2026-06-27T00:00:00Z",
        safe_user_message="checked",
        visibility="silent",
        policy_reason="status only",
    )


def _unavailable_status(family: str) -> SourceStatus:
    return source_status(
        source_id=f"{family}-probe",
        source_family=family,
        scope={"repo": "acme/widgets"},
        status="unavailable",
        observed_at="2026-06-27T00:00:00Z",
        safe_user_message="no access",
        visibility="silent",
        policy_reason="status only",
    )


def test_heads_up_when_a_collision_is_found() -> None:
    answer = broker_answer(_request(), [_collision_signal()], [_fresh_status("git_hosting")])
    text = hook_signal(answer, file_path="src/app.py", token_present=True)
    assert "src/app.py" in text
    assert "PR #7" in text
    assert "ground" not in text.lower() and "broker" not in text.lower()


def test_cant_verify_when_github_unreachable_no_token() -> None:
    answer = broker_answer(_request(), [], [_unavailable_status("git_hosting")])
    text = hook_signal(answer, file_path="src/app.py", token_present=False)
    assert "GitHub" in text
    assert "GITHUB_TOKEN" in text
    assert "keep working" in text


def test_cant_verify_with_token_present_is_transient() -> None:
    answer = broker_answer(_request(), [], [_unavailable_status("git_hosting")])
    text = hook_signal(answer, file_path="src/app.py", token_present=True)
    assert "GitHub" in text
    assert "transient" in text
    assert "install-hook" not in text  # the token-present message must not tell them to install


def test_ready_names_the_clear_checks_no_lowstakes_hedge() -> None:
    answer = broker_answer(_request(), [], [_fresh_status("git_hosting")])
    text = hook_signal(answer, file_path="src/app.py", token_present=True)
    assert "looks clear" in text.lower()
    assert "src/app.py" in text
    assert "pull request" in text.lower()
    assert "couldn't" not in text.lower()


def _pending_status(family: str) -> SourceStatus:
    return source_status(
        source_id=f"{family}-probe",
        source_family=family,
        scope={"repo": "acme/widgets"},
        status="pending",
        observed_at="2026-06-27T00:00:00Z",
        safe_user_message="running",
        visibility="warning_when_relevant",
        policy_reason="status only",
    )


def test_pending_gate_says_checks_running_not_unreachable() -> None:
    answer = broker_answer(_request(), [], [_pending_status("ci_deploy")])
    text = hook_signal(answer, file_path="src/app.py", token_present=True)
    assert "still running" in text.lower()
    assert "couldn't reach GitHub" not in text


def test_found_conflict_plus_pending_gate_surfaces_both() -> None:
    answer = broker_answer(
        _request(),
        [_collision_signal()],
        [_fresh_status("git_hosting"), _pending_status("ci_deploy")],
    )
    text = hook_signal(answer, file_path="src/app.py", token_present=True)
    assert "PR #7" in text  # the finding
    assert "still running" in text.lower()  # the pending gate is not dropped in heads_up


def test_unreachable_conflict_plus_pending_gate_mentions_both() -> None:
    answer = broker_answer(
        _request(), [], [_unavailable_status("git_hosting"), _pending_status("ci_deploy")]
    )
    text = hook_signal(answer, file_path="src/app.py", token_present=True)
    assert "GitHub" in text  # the unreachable conflict is surfaced
    assert "still running" in text.lower()  # and the pending gate, not falsely "couldn't check"
    # the gate is pending, not unreachable: don't claim we couldn't check failing checks.
    assert "failing checks" not in text
