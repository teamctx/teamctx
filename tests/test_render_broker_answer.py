from __future__ import annotations

from teamctx.connectors._contract import metadata_only_policy, source_status
from teamctx.contract_render import render_broker_answer
from teamctx.core.authority import AuthorityDecl
from teamctx.core.broker import broker_answer
from teamctx.core.contracts import RequestContext, SourceSignal, SourceStatus


def _request(paths=("src/app.py",), issues=()) -> RequestContext:
    return RequestContext(
        schema_version="teamctx.request_context.v0", request_id="t", repo="acme/widgets",
        branch="feature", task="work", paths=list(paths), linked_issues=list(issues),
        requested_at="2026-06-28T00:00:00Z", requesting_principal=None,
    )


def _collision_signal() -> SourceSignal:
    return SourceSignal(
        schema_version="teamctx.source_signal.v0", id="sig_pr_7", signal_type="collision",
        source_family="git_hosting", scope={"repo": "acme/widgets", "files": ["src/app.py"]},
        evidence_summary="PR #7 changes src/app.py", source_display="github acme/widgets#7",
        freshness="fresh", confidence="high", visibility="visible",
        created_at="2026-06-28T00:00:00Z", observed_at="2026-06-28T00:00:00Z",
        expires_at="next_refresh", policy=metadata_only_policy("pr metadata is evidence"),
    )


def _fresh(family: str) -> SourceStatus:
    return source_status(
        source_id=f"{family}-probe", source_family=family, scope={"repo": "acme/widgets"},
        status="fresh", observed_at="2026-06-28T00:00:00Z", safe_user_message="checked",
        visibility="silent", policy_reason="status only",
    )


def _unavailable(family: str) -> SourceStatus:
    return source_status(
        source_id=f"{family}-probe", source_family=family, scope={"repo": "acme/widgets"},
        status="unavailable", observed_at="2026-06-28T00:00:00Z", safe_user_message="no access",
        visibility="silent", policy_reason="status only",
    )


_EM_DASH = chr(0x2014)  # checked without the literal to keep the file em-dash-free


def _no_jargon(text: str) -> None:
    for bad in ("UNKNOWN", "NOT CLEAR", "incomplete[", "git_hosting", "ci_deploy",
                "coverage incomplete", "absence is not an all-clear", _EM_DASH):
        assert bad not in text, f"leaked: {bad!r}"


def test_ready_headline_names_clear_checks_and_lists_gaps() -> None:
    text = render_broker_answer(broker_answer(_request(), [], [_fresh("git_hosting")]))
    assert text.startswith("Looks clear to start.")
    assert "no open PRs touch your files" in text
    assert "Not checked:" in text and "no issue is linked to this branch" in text
    _no_jargon(text)


def test_heads_up_surfaces_the_pr_with_action() -> None:
    text = render_broker_answer(
        broker_answer(_request(), [_collision_signal()], [_fresh("git_hosting")])
    )
    assert text.startswith("Before you start, here is what to handle first:")
    assert "PR #7" in text
    assert "gh pr view 7" in text
    _no_jargon(text)


def test_cant_verify_when_github_unreachable() -> None:
    text = render_broker_answer(broker_answer(_request(), [], [_unavailable("git_hosting")]))
    assert text.startswith("Heads up: I couldn't check the important things:")
    assert "couldn't reach GitHub" in text
    assert "teamctx install-hook" in text
    _no_jargon(text)


def test_non_important_unreachable_is_surfaced_not_hidden() -> None:
    # issue source down (non-important) keeps kind=ready, but the render must still say it
    # couldn't check criteria; a silent clear here would be a false all-clear.
    text = render_broker_answer(
        broker_answer(_request(), [], [_fresh("git_hosting"), _unavailable("issue_tracker")])
    )
    assert text.startswith("Looks clear to start.")
    assert "Couldn't check: spec changes" in text
    _no_jargon(text)


def test_authority_section_surfaces_a_conflict() -> None:
    decls = [
        AuthorityDecl(subject="rounding-cap", source="ticket", priority=10, value="5", fresh=True),
        AuthorityDecl(subject="rounding-cap", source="policy", priority=10, value="3", fresh=True),
    ]
    text = render_broker_answer(broker_answer(_request(), [], [_fresh("git_hosting")], decls))
    assert "Authority" in text
    assert "rounding-cap" in text
    assert "CONFLICTED" in text


def test_no_authority_section_without_declarations() -> None:
    text = render_broker_answer(broker_answer(_request(), [], [_fresh("git_hosting")]))
    assert "Authority" not in text
