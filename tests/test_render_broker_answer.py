from __future__ import annotations

from teamctx.connectors._contract import metadata_only_policy, source_status
from teamctx.contract_render import render_broker_answer
from teamctx.core.authority import AuthorityDecl
from teamctx.core.broker import broker_answer
from teamctx.core.contracts import RequestContext, SourceSignal, SourceStatus
from teamctx.hook_signal import hook_signal


def _request(
    paths=("src/app.py",),
    issues=(),
    provenance=None,
    forge: str = "github",
) -> RequestContext:
    return RequestContext(
        schema_version="teamctx.request_context.v0", request_id="t", repo="acme/widgets",
        forge=forge, branch="feature", task="work", paths=list(paths), linked_issues=list(issues),
        input_provenance=provenance or {},
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


def _criteria_signal() -> SourceSignal:
    # text ends in a period and source_display carries an ISSUE number (#42, not a PR).
    return SourceSignal(
        schema_version="teamctx.source_signal.v0", id="sig_issue_42",
        signal_type="criteria_changed",
        source_family="issue_tracker", scope={"repo": "acme/widgets", "issue": "#42"},
        evidence_summary="Issue #42 acceptance criteria changed.",
        source_display="github acme/widgets#42",
        freshness="fresh", confidence="high", visibility="visible",
        created_at="2026-06-28T00:00:00Z", observed_at="2026-06-28T00:00:00Z",
        expires_at="next_refresh", policy=metadata_only_policy("issue metadata is evidence"),
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


def _unbounded(family: str, message: str) -> SourceStatus:
    return source_status(
        source_id=f"{family}-probe",
        source_family=family,
        scope={"repo": "acme/widgets"},
        status="unbounded",
        observed_at="2026-06-28T00:00:00Z",
        safe_user_message=message,
        visibility="warning_when_relevant",
        policy_reason="status only",
    )


def _disabled(family: str, message: str) -> SourceStatus:
    return source_status(
        source_id=f"{family}-probe",
        source_family=family,
        scope={"repo": "acme/widgets"},
        status="disabled",
        observed_at="2026-06-28T00:00:00Z",
        safe_user_message=message,
        visibility="warning_when_relevant",
        policy_reason="status only",
    )


def _status_note(status: str) -> SourceStatus:
    message = (
        "Your own open PR #12 for this branch touches these files; "
        "not flagged as a collision."
    )
    return source_status(
        source_id="github_pr_metadata",
        source_family="git_hosting",
        scope={"repo": "acme/widgets", "own_branch_prs": ["12"]},
        status=status,
        observed_at="2026-06-28T00:00:00Z",
        safe_user_message=message,
        visibility="warning_when_relevant",
        policy_reason="status only",
    )


def test_render_fyi_line_for_fresh_warning_note() -> None:
    text = render_broker_answer(broker_answer(_request(), [], [_status_note("fresh")]))
    assert "FYI: Your own open PR #12" in text
    assert "no other open PRs touch your files" in text
    _no_jargon(text)


def test_render_no_fyi_for_stale_status() -> None:
    text = render_broker_answer(broker_answer(_request(), [], [_status_note("stale")]))
    assert "FYI:" not in text
    _no_jargon(text)


_EM_DASH = chr(0x2014)  # checked without the literal to keep the file em-dash-free


def _no_jargon(text: str) -> None:
    for bad in ("UNKNOWN", "NOT CLEAR", "incomplete[", "git_hosting", "ci_deploy",
                "coverage incomplete", "absence is not an all-clear", _EM_DASH):
        assert bad not in text, f"leaked: {bad!r}"


def test_ready_headline_names_clear_checks_and_lists_gaps() -> None:
    text = render_broker_answer(broker_answer(_request(), [], [_fresh("git_hosting")]))
    assert text.startswith("Looks clear to start.")
    assert "no other open PRs touch your files" in text
    assert "Not checked:" in text and "no issue is linked to this branch" in text
    _no_jargon(text)


def test_not_checked_line_uses_disabled_note_verbatim() -> None:
    note = (
        "spec changes (no issue could be derived from your branch or commits; name one "
        "with --issue)"
    )
    text = render_broker_answer(broker_answer(_request(), [], [_disabled("issue_tracker", note)]))
    assert note in text
    assert "no issue is linked to this branch" not in text
    _no_jargon(text)


def test_not_checked_line_uses_derived_issue_without_since_note() -> None:
    note = "spec changes (issue #42 was derived, but the start time couldn't be; pass --since)"
    text = render_broker_answer(broker_answer(_request(), [], [_disabled("issue_tracker", note)]))
    assert note in text
    assert "no issue is linked to this branch" not in text
    _no_jargon(text)


def test_heads_up_surfaces_the_pr_with_action() -> None:
    text = render_broker_answer(
        broker_answer(_request(), [_collision_signal()], [_fresh("git_hosting")])
    )
    assert text.startswith("Before you start, here is what to handle first:")
    assert "PR #7" in text
    # the hint carries --repo so it works from any directory (and matches open-source)
    assert "gh pr view 7 --repo acme/widgets" in text
    _no_jargon(text)


def test_non_conflict_finding_has_no_pr_hint_and_clean_punctuation() -> None:
    # a criteria finding: source_display carries an ISSUE number, not a PR, so no `gh pr view`,
    # and the action must not produce `.:` against an evidence summary that ends in a period.
    text = render_broker_answer(
        broker_answer(_request(issues=("#42",)), [_criteria_signal()], [_fresh("issue_tracker")])
    )
    assert text.startswith("Before you start, here is what to handle first:")
    assert "Issue #42" in text
    assert "re-check the criteria before you rely on them" in text
    assert "gh pr view" not in text
    assert ".:" not in text
    _no_jargon(text)


def test_cant_verify_when_github_unreachable() -> None:
    text = render_broker_answer(broker_answer(_request(), [], [_unavailable("git_hosting")]))
    assert text.startswith("Heads up: I can't confirm the important things yet:")
    assert "couldn't reach GitHub" in text
    assert "GITHUB_TOKEN" in text
    _no_jargon(text)


def test_gitlab_clear_conflict_copy_uses_mrs() -> None:
    text = render_broker_answer(
        broker_answer(_request(forge="gitlab"), [], [_fresh("git_hosting")])
    )
    assert "no other open MRs touch your files" in text
    assert "open PRs" not in text
    _no_jargon(text)


def test_gitlab_unreachable_copy_and_fix_line() -> None:
    text = render_broker_answer(
        broker_answer(
            _request(forge="gitlab"),
            [],
            [_unavailable("git_hosting"), _unavailable("ci_deploy")],
        )
    )

    assert text.startswith("Heads up: I can't confirm the important things yet:")
    assert "Open MRs and pipeline state:" in text
    assert "couldn't reach GitLab" in text
    assert "set GITLAB_TOKEN, or GITLAB_TOKEN_FILE with a path to a token file" in text
    assert "GitHub" not in text
    assert "GITHUB_TOKEN" not in text
    _no_jargon(text)


def test_gitlab_gate_unreachable_line_uses_pipeline_state() -> None:
    text = render_broker_answer(
        broker_answer(
            _request(forge="gitlab"),
            [_collision_signal()],
            [_fresh("git_hosting"), _unavailable("ci_deploy")],
        )
    )

    assert "Couldn't check: pipeline state (couldn't reach GitLab)." in text
    assert "failing checks (couldn't reach GitHub)" not in text
    _no_jargon(text)


def test_cant_verify_unbounded_conflict_has_bullet_and_no_double_print() -> None:
    note = (
        "Checked the 300 most recently updated open PRs; more exist, so this is not a "
        "complete check."
    )

    text = render_broker_answer(broker_answer(_request(), [], [_unbounded("git_hosting", note)]))

    assert text.startswith("Heads up: I can't confirm the important things yet:")
    assert f"Open PRs: {note} Glance at GitHub if this file is sensitive." in text
    assert "Partially checked:" not in text
    assert text.count(note) == 1
    _no_jargon(text)


def test_non_important_unbounded_gets_partially_checked_line() -> None:
    note = (
        "Checked the 20 most recently updated issues; more exist, so this is not a "
        "complete check."
    )

    text = render_broker_answer(
        broker_answer(_request(), [], [_fresh("git_hosting"), _unbounded("issue_tracker", note)])
    )

    assert text.startswith("Looks clear to start.")
    assert f"Partially checked: {note}" in text
    assert "I can't confirm the important things yet" not in text
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


def test_heads_up_still_surfaces_unreachable_important_check() -> None:
    text = render_broker_answer(
        broker_answer(
            _request(), [_collision_signal()], [_fresh("git_hosting"), _unavailable("ci_deploy")]
        )
    )
    assert text.startswith("Before you start, here is what to handle first:")
    assert "PR #7" in text
    assert "Couldn't check: failing checks" in text
    _no_jargon(text)


def test_heads_up_uses_also_checked_label_for_remaining_clear_checks() -> None:
    # found conflict -> heads_up; gate clear -> the clear summary uses "Also checked:" not "Checked"
    text = render_broker_answer(
        broker_answer(
            _request(), [_collision_signal()], [_fresh("git_hosting"), _fresh("ci_deploy")]
        )
    )
    assert text.startswith("Before you start, here is what to handle first:")
    assert "Also checked: no failing checks found" in text
    _no_jargon(text)


def test_criteria_clear_line_names_single_derived_issue_provenance() -> None:
    request = _request(issues=("#123",), provenance={"issue:#123": "your branch name"})

    text = render_broker_answer(broker_answer(request, [], [_fresh("issue_tracker")]))

    assert "the linked issue's criteria are unchanged (issue #123 from your branch name)" in text
    _no_jargon(text)


def test_criteria_clear_line_names_multiple_derived_issue_provenance() -> None:
    request = _request(
        issues=("#12", "#34"),
        provenance={
            "issue:#12": "your branch name",
            "issue:#34": "a commit message trailer",
        },
    )

    text = render_broker_answer(broker_answer(request, [], [_fresh("issue_tracker")]))

    assert (
        "the linked issue's criteria are unchanged "
        "(issues #12 from your branch name, #34 from a commit trailer)"
    ) in text
    _no_jargon(text)


def test_criteria_clear_line_omits_suffix_for_explicit_issue() -> None:
    request = _request(issues=("#123",))

    text = render_broker_answer(broker_answer(request, [], [_fresh("issue_tracker")]))

    assert "the linked issue's criteria are unchanged." in text
    assert "from your branch name" not in text
    _no_jargon(text)


def test_hook_signal_does_not_include_criteria_provenance_suffix() -> None:
    request = _request(issues=("#123",), provenance={"issue:#123": "your branch name"})
    answer = broker_answer(request, [], [_fresh("issue_tracker")])

    signal = hook_signal(answer, file_path="src/app.py", token_present=True)

    assert "the linked issue's criteria are unchanged" in signal
    assert "from your branch name" not in signal


def test_cant_verify_gate_only_bullet() -> None:
    # gate alone unreachable (conflict clear) -> cant_verify with the gate-only bullet, not combined
    text = render_broker_answer(
        broker_answer(_request(), [], [_fresh("git_hosting"), _unavailable("ci_deploy")])
    )
    assert text.startswith("Heads up: I can't confirm the important things yet:")
    assert "Failing checks:" in text
    assert "Open PRs and failing checks:" not in text
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


def _pending(family: str) -> SourceStatus:
    return source_status(
        source_id=f"{family}-probe", source_family=family, scope={"repo": "acme/widgets"},
        status="pending", observed_at="2026-06-28T00:00:00Z", safe_user_message="running",
        visibility="warning_when_relevant", policy_reason="status only",
    )


def _not_applicable(family: str) -> SourceStatus:
    return source_status(
        source_id=f"{family}-probe", source_family=family, scope={"repo": "acme/widgets"},
        status="not_applicable", observed_at="2026-06-28T00:00:00Z", safe_user_message="n/a",
        visibility="silent", policy_reason="status only",
    )


def test_cant_verify_pending_gate_shows_still_running() -> None:
    text = render_broker_answer(broker_answer(_request(), [], [_pending("ci_deploy")]))
    assert text.startswith("Heads up: I can't confirm the important things yet:")
    assert "still running" in text.lower()
    assert "no failing checks found" not in text  # never a false green for a pending gate
    _no_jargon(text)


def test_not_applicable_gets_its_own_line_not_cant_verify() -> None:
    # A not_applicable coverage state on a non-important check is its own line, never cant_verify.
    # docs no longer emits not_applicable, so the render uses the generic fallback phrase (the
    # not_applicable render path is kept for future kinds).
    text = render_broker_answer(
        broker_answer(_request(), [], [_fresh("git_hosting"), _not_applicable("docs")])
    )
    assert "Not applicable: docs" in text
    assert "docs (not applicable to the files in scope)" in text
    assert "I can't confirm the important things yet" not in text
    assert "the docs you rely on are current" not in text
    _no_jargon(text)


def test_heads_up_finding_plus_pending_gate_surfaces_still_running() -> None:
    # a found conflict makes the kind heads_up; the pending gate must still be surfaced once.
    text = render_broker_answer(
        broker_answer(
            _request(), [_collision_signal()], [_fresh("git_hosting"), _pending("ci_deploy")]
        )
    )
    assert text.startswith("Before you start, here is what to handle first:")
    assert "PR #7" in text
    assert "Still running:" in text
    _no_jargon(text)


def test_cant_verify_unreachable_conflict_plus_pending_gate_shows_both() -> None:
    text = render_broker_answer(
        broker_answer(_request(), [], [_unavailable("git_hosting"), _pending("ci_deploy")])
    )
    assert text.startswith("Heads up: I can't confirm the important things yet:")
    assert "Open PRs:" in text  # the unreachable conflict bullet
    assert "still running" in text.lower()  # the pending gate bullet, not dropped
    _no_jargon(text)


def test_heads_up_finding_plus_not_applicable_docs() -> None:
    text = render_broker_answer(
        broker_answer(
            _request(), [_collision_signal()], [_fresh("git_hosting"), _not_applicable("docs")]
        )
    )
    assert text.startswith("Before you start, here is what to handle first:")
    assert "PR #7" in text
    assert "Not applicable: docs" in text
    _no_jargon(text)


def test_nothing_checked_never_reads_clear() -> None:
    # All checks not configured (e.g. a GitLab repo before the connector exists): the ready
    # headline would be false comfort, so the render says nothing was checked.
    text = render_broker_answer(broker_answer(_request(), [], []))
    assert not text.startswith("Looks clear to start.")
    assert text.startswith("Nothing checked yet; here's why:")
    assert "Not checked:" in text
    _no_jargon(text)


def _docs_status(source_id: str, status: str) -> SourceStatus:
    return source_status(
        source_id=source_id, source_family="docs", scope={"repo": "acme/widgets"},
        status=status, observed_at="2026-06-28T00:00:00Z", safe_user_message="m",
        visibility="silent", policy_reason="status only",
    )


def test_confluence_failure_names_confluence_not_the_local_folder() -> None:
    # a failed Confluence scan must never read "couldn't read the docs folder"
    text = render_broker_answer(
        broker_answer(
            _request(), [], [_fresh("git_hosting"), _docs_status("confluence_pages", "unavailable")]
        )
    )
    assert "couldn't reach Confluence" in text
    assert "couldn't read the docs folder" not in text
    _no_jargon(text)


def test_local_docs_failure_names_the_local_folder() -> None:
    text = render_broker_answer(
        broker_answer(
            _request(), [], [_fresh("git_hosting"), _docs_status("docs_supersession", "unavailable")]
        )
    )
    assert "couldn't read the local docs folder" in text
    _no_jargon(text)
