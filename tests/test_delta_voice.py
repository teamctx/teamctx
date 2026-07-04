"""The delta voice: the pinned "since you started: ..." copy, spoken first and once, and the
three interaction pins (bullet suppression, ready-guard independence, kind stability)."""

from __future__ import annotations

from teamctx.ambient import Delta, FindingMaterial, build_delta_document
from teamctx.assessment import assess
from teamctx.connectors._contract import metadata_only_policy, source_status
from teamctx.contract_render import delta_lines, render_broker_answer
from teamctx.core.broker import BrokerAnswer, broker_answer
from teamctx.core.contracts import RequestContext, SourceSignal, SourceStatus
from teamctx.hook_signal import hook_signal

OBS = "2026-07-04T00:00:00Z"


def _request(paths: tuple[str, ...] = ("src/auth/token.py",)) -> RequestContext:
    return RequestContext(
        schema_version="teamctx.request_context.v0", request_id="t", repo="acme/widgets",
        branch="feature", task="work", paths=list(paths), linked_issues=[],
        requested_at=OBS, requesting_principal=None,
    )


def _pr(number: int = 7, paths: tuple[str, ...] = ("src/auth/token.py",)) -> FindingMaterial:
    return FindingMaterial(
        key=f"conflict:{number}", source_display=f"GitHub PR #{number}", paths=paths
    )


def _line(delta: Delta, checks: tuple = (), forge: str = "github") -> str:
    return delta_lines((delta,), checks, forge)[0]


# --- one test per pinned copy string ---


def test_appear_conflict_copy() -> None:
    assert _line(Delta("appear", "conflict", _pr())) == (
        "since you started: GitHub PR #7 appeared, touching src/auth/token.py"
    )


def test_appear_gate_copy() -> None:
    gate = FindingMaterial(key="gate:build", source_display="CI: build", gate="build")
    assert _line(Delta("appear", "gate", gate)) == (
        "since you started: check 'build' started failing on this branch"
    )


def test_appear_criteria_copy() -> None:
    criteria = FindingMaterial(
        key="criteria:#12", source_display="GitHub issue #12", detail="acceptance criteria edited"
    )
    assert _line(Delta("appear", "criteria", criteria)) == (
        "since you started: GitHub issue #12 changed: acceptance criteria edited"
    )


def test_appear_docs_copy_with_and_without_replacement() -> None:
    with_replacement = FindingMaterial(
        key="docs:spec.md", doc="spec.md", superseded_by="spec-v2.md"
    )
    without = FindingMaterial(key="docs:spec.md", doc="spec.md")
    assert _line(Delta("appear", "docs", with_replacement)) == (
        "since you started: spec.md was superseded by spec-v2.md"
    )
    assert _line(Delta("appear", "docs", without)) == "since you started: spec.md was superseded"


def test_disappear_copy_per_check() -> None:
    gate = FindingMaterial(key="gate:build", source_display="CI: build", gate="build")
    criteria = FindingMaterial(key="criteria:#12", source_display="GitHub issue #12")
    docs = FindingMaterial(key="docs:spec.md", doc="spec.md")
    assert _line(Delta("disappear", "conflict", _pr())) == (
        "since you started: GitHub PR #7 no longer touches your files"
    )
    assert _line(Delta("disappear", "gate", gate)) == (
        "since you started: check 'build' is green again"
    )
    assert _line(Delta("disappear", "criteria", criteria)) == (
        "since you started: GitHub issue #12 is no longer flagged"
    )
    assert _line(Delta("disappear", "docs", docs)) == (
        "since you started: the note about spec.md cleared"
    )


def test_recovery_to_clear_copy() -> None:
    delta = Delta("transition", "gate", FindingMaterial(key="gate:__source__"))
    assert _line(delta) == "GitHub is back: no failing checks found"


def test_coverage_shrank_copy_github_and_gitlab() -> None:
    delta = Delta(
        "coverage_shrank", "conflict", FindingMaterial(key="conflict:__source__"),
        note="couldn't reach GitHub",
    )
    assert _line(delta) == (
        "since you started: open pull requests can no longer be verified (couldn't reach GitHub)"
    )
    gitlab = Delta(
        "coverage_shrank", "conflict", FindingMaterial(key="conflict:__source__"),
        note="couldn't reach GitLab",
    )
    assert _line(gitlab, forge="gitlab") == (
        "since you started: open merge requests can no longer be verified (couldn't reach GitLab)"
    )


def test_coverage_shrank_uses_a_default_note_when_none() -> None:
    delta = Delta("coverage_shrank", "gate", FindingMaterial(key="gate:__source__"))
    assert _line(delta) == (
        "since you started: failing checks can no longer be verified (couldn't reach GitHub)"
    )


# --- building answers that carry minted deltas, to exercise the assess lane and the render ---


def _collision_signal() -> SourceSignal:
    return SourceSignal(
        schema_version="teamctx.source_signal.v0", id="sig_pr_7", signal_type="collision",
        source_family="git_hosting",
        scope={"provider": "github", "repo": "acme/widgets", "pr_number": 7,
               "files": ["src/auth/token.py"]},
        evidence_summary="Open PR #7 changed src/auth/token.py.", source_display="GitHub PR #7",
        freshness="fresh", confidence="high", visibility="visible",
        created_at=OBS, observed_at=OBS, expires_at="next_refresh",
        policy=metadata_only_policy("pr metadata is evidence"),
    )


def _gate_signal() -> SourceSignal:
    return SourceSignal(
        schema_version="teamctx.source_signal.v0", id="sig_gate_build", signal_type="missed_gate",
        source_family="ci_deploy", scope={"repo": "acme/widgets", "gate": "build"},
        evidence_summary="Check 'build' is failing on this branch.", source_display="CI: build",
        freshness="fresh", confidence="high", visibility="visible",
        created_at=OBS, observed_at=OBS, expires_at="next_refresh",
        policy=metadata_only_policy("gate metadata is evidence"),
    )


def _fresh(family: str) -> SourceStatus:
    return source_status(
        source_id=f"{family}-probe", source_family=family, scope={"repo": "acme/widgets"},
        status="fresh", observed_at=OBS, safe_user_message="checked",
        visibility="silent", policy_reason="status only",
    )


def _unavailable(family: str) -> SourceStatus:
    return source_status(
        source_id=f"{family}-probe", source_family=family, scope={"repo": "acme/widgets"},
        status="unavailable", observed_at=OBS, safe_user_message="no access",
        visibility="silent", policy_reason="status only",
    )


def _with_deltas(
    base_signals: list[SourceSignal],
    base_statuses: list[SourceStatus],
    deltas: tuple[Delta, ...],
    request: RequestContext | None = None,
) -> BrokerAnswer:
    request = request or _request()
    document = build_delta_document(request, deltas, observed_at=OBS)
    return broker_answer(request, [*base_signals, *document.source_signals], base_statuses)


def test_appearance_suppresses_the_steady_finding_bullet() -> None:
    # PR #7 is a live collision (found) AND it appeared this run: the delta speaks it, and the
    # steady found bullet for #7 is suppressed. One fact, one voice.
    answer = _with_deltas(
        [_collision_signal()], [_fresh("git_hosting")], (Delta("appear", "conflict", _pr()),)
    )

    signal = hook_signal(answer, file_path="src/auth/token.py", token_present=True)

    assert signal == "since you started: GitHub PR #7 appeared, touching src/auth/token.py"
    assert "  • Open PR #7" not in signal  # the steady bullet is gone


def test_kind_never_changes_because_of_a_delta() -> None:
    base = broker_answer(_request(), [_collision_signal()], [_fresh("git_hosting")])
    with_delta = _with_deltas(
        [_collision_signal()], [_fresh("git_hosting")], (Delta("disappear", "gate", _pr()),)
    )
    assert assess(base).kind == assess(with_delta).kind == "heads_up"


def test_a_lone_disappearance_speaks_over_a_quiet_world() -> None:
    # nothing is clear or found (the base render is empty), but a disappearance still speaks: the
    # delta lane is independent of the steady ready-guard.
    answer = _with_deltas([], [], (Delta("disappear", "conflict", _pr()),))

    assert hook_signal(answer, file_path="src/auth/token.py", token_present=True) == (
        "since you started: GitHub PR #7 no longer touches your files"
    )


def test_coverage_shrank_suppresses_the_steady_cant_verify_line() -> None:
    delta = Delta(
        "coverage_shrank", "conflict", FindingMaterial(key="conflict:__source__"),
        note="couldn't reach GitHub",
    )
    answer = _with_deltas([], [_unavailable("git_hosting")], (delta,))

    signal = hook_signal(answer, file_path="src/auth/token.py", token_present=True)

    assert signal == (
        "since you started: open pull requests can no longer be verified (couldn't reach GitHub)"
    )
    assert "couldn't reach GitHub just now" not in signal  # the steady can't-verify line is gone


def test_recovery_to_a_finding_carries_the_finding_line_and_suppresses_the_bullet() -> None:
    delta = Delta("transition", "gate", FindingMaterial(key="gate:__source__"))
    answer = _with_deltas([_gate_signal()], [_fresh("ci_deploy")], (delta,))

    signal = hook_signal(answer, file_path="src/auth/token.py", token_present=True)

    assert signal == "GitHub is back: Check 'build' is failing on this branch"
    assert "  • Check 'build' is failing" not in signal  # steady found bullet suppressed


def test_render_broker_answer_speaks_the_delta_first() -> None:
    answer = _with_deltas(
        [_collision_signal()], [_fresh("git_hosting")], (Delta("appear", "conflict", _pr()),)
    )

    report = render_broker_answer(answer)

    assert report.splitlines()[0] == (
        "since you started: GitHub PR #7 appeared, touching src/auth/token.py"
    )


def test_cli_report_is_unchanged_without_a_delta_document() -> None:
    base = broker_answer(_request(), [_collision_signal()], [_fresh("git_hosting")])
    assert "since you started" not in render_broker_answer(base)
