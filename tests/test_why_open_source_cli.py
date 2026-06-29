"""Tests for the `why` and `open-source` CLI commands.

Covers: collision scenario end-to-end (renders evidence + gh command), bad selector,
NoFindingMatch when check was clear (may have cleared), NoFindingMatch when source was
unreachable (could not check), and AmbiguousFinding (disambiguation message).

Renderer unit tests for render_why and render_open_source are included below the CLI tests.
"""

from __future__ import annotations

from pathlib import Path

import pytest
from click.testing import CliRunner

from teamctx.cli import main

# ---------------------------------------------------------------------------
# Shared helpers
# ---------------------------------------------------------------------------


def _stub_connectors(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
    *,
    prs: list | None = None,
) -> None:
    """Stub all network connectors; set a fake token so the connectors are reached."""

    monkeypatch.chdir(tmp_path)

    import teamctx.connectors.github as gh
    import teamctx.connectors.github_checks as gc
    import teamctx.connectors.github_issues as gi
    import teamctx.runner as runner_mod
    from teamctx.connectors.github import ForgeReviewFetch
    from teamctx.connectors.github_checks import CheckRunsFetch

    monkeypatch.setattr(
        gh,
        "fetch_github_pull_requests",
        lambda **kw: ForgeReviewFetch(pull_requests=prs or [], truncated=False),
    )
    monkeypatch.setattr(
        gc,
        "fetch_failing_check_runs",
        lambda **kw: CheckRunsFetch(failing=[], truncated=False),
    )
    monkeypatch.setattr(gi, "fetch_issue_changes", lambda **kw: [])
    real_docs_probe = runner_mod.run_docs_supersession_probe
    monkeypatch.setattr(
        runner_mod,
        "run_docs_supersession_probe",
        lambda **kw: real_docs_probe(reader=lambda root: [], **kw),
    )
    monkeypatch.setenv("GITHUB_TOKEN", "t")


def _make_pr(
    number: int = 7,
    repo: str = "acme/widgets",
    paths: tuple[str, ...] = ("src/app.py",),
) -> object:
    from teamctx.connectors.forge_review import ForgeReviewPullRequest

    return ForgeReviewPullRequest(
        provider="github",
        repo=repo,
        number=number,
        state="open",
        url=f"https://github.com/{repo}/pull/{number}",
        title=None,
        changed_paths=paths,
        created_at="2026-01-01T00:00:00Z",
        updated_at="2026-01-01T00:00:00Z",
    )


_BASE_ARGS = ["--github-repo", "acme/widgets", "--path", "src/app.py"]


# ---------------------------------------------------------------------------
# why: collision scenario
# ---------------------------------------------------------------------------


def test_why_pr_renders_finding_text(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    _stub_connectors(monkeypatch, tmp_path, prs=[_make_pr()])
    result = CliRunner().invoke(
        main, ["why", "pr:7"] + _BASE_ARGS, catch_exceptions=False
    )
    assert result.exit_code == 0, result.output
    assert "Open PR #7 changed src/app.py" in result.output


def test_why_pr_renders_why_it_matters(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    _stub_connectors(monkeypatch, tmp_path, prs=[_make_pr()])
    result = CliRunner().invoke(
        main, ["why", "pr:7"] + _BASE_ARGS, catch_exceptions=False
    )
    assert result.exit_code == 0, result.output
    assert "Why it matters:" in result.output
    assert "src/app.py" in result.output


def test_why_pr_renders_flagged_reason(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    _stub_connectors(monkeypatch, tmp_path, prs=[_make_pr()])
    result = CliRunner().invoke(
        main, ["why", "pr:7"] + _BASE_ARGS, catch_exceptions=False
    )
    assert result.exit_code == 0, result.output
    assert "Why teamctx flagged it:" in result.output
    assert "same repository and file path" in result.output


def test_why_pr_renders_source_with_freshness(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    _stub_connectors(monkeypatch, tmp_path, prs=[_make_pr()])
    result = CliRunner().invoke(
        main, ["why", "pr:7"] + _BASE_ARGS, catch_exceptions=False
    )
    assert result.exit_code == 0, result.output
    assert "GitHub PR #7" in result.output
    assert "fresh" in result.output
    assert "confidence" in result.output


def test_why_pr_renders_metadata_only_note(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    _stub_connectors(monkeypatch, tmp_path, prs=[_make_pr()])
    result = CliRunner().invoke(
        main, ["why", "pr:7"] + _BASE_ARGS, catch_exceptions=False
    )
    assert result.exit_code == 0, result.output
    assert "metadata only" in result.output


# ---------------------------------------------------------------------------
# open-source: collision scenario
# ---------------------------------------------------------------------------


def test_open_source_pr_renders_gh_command(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    _stub_connectors(monkeypatch, tmp_path, prs=[_make_pr()])
    result = CliRunner().invoke(
        main, ["open-source", "pr:7"] + _BASE_ARGS, catch_exceptions=False
    )
    assert result.exit_code == 0, result.output
    assert "gh pr view 7 --repo acme/widgets" in result.output


def test_open_source_pr_renders_url(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    _stub_connectors(monkeypatch, tmp_path, prs=[_make_pr()])
    result = CliRunner().invoke(
        main, ["open-source", "pr:7"] + _BASE_ARGS, catch_exceptions=False
    )
    assert result.exit_code == 0, result.output
    assert "https://github.com/acme/widgets/pull/7" in result.output


def test_open_source_pr_renders_body_availability_note(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    _stub_connectors(monkeypatch, tmp_path, prs=[_make_pr()])
    result = CliRunner().invoke(
        main, ["open-source", "pr:7"] + _BASE_ARGS, catch_exceptions=False
    )
    assert result.exit_code == 0, result.output
    assert "metadata only" in result.output
    assert "status-only by policy" in result.output


# ---------------------------------------------------------------------------
# Bad selector
# ---------------------------------------------------------------------------


def test_bad_selector_exits_nonzero(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    monkeypatch.chdir(tmp_path)
    result = CliRunner().invoke(
        main, ["why", "notaselector"] + _BASE_ARGS
    )
    assert result.exit_code != 0
    # The allowed-forms message must appear.
    output = result.output.lower()
    assert "pr:n" in output or "expected one of" in output or "pr:" in result.output


def test_bad_selector_unknown_kind_exits_nonzero(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    monkeypatch.chdir(tmp_path)
    result = CliRunner().invoke(
        main, ["why", "branch:main"] + _BASE_ARGS
    )
    assert result.exit_code != 0
    assert "branch" in result.output or "Unknown" in result.output


def test_pr_selector_non_numeric_fails_clean_at_parse(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    """`why pr:abc` must fail at parse with a clean message, before any broker run. No
    connectors are stubbed and no token is set: if it reached the broker the no-match path
    would emit a different message, so the parse-time message proves it short-circuited."""

    monkeypatch.chdir(tmp_path)
    result = CliRunner().invoke(
        main, ["why", "pr:abc"] + _BASE_ARGS
    )
    assert result.exit_code != 0
    assert "expects a number" in result.output
    # Clean ClickException, not a leaked traceback.
    assert "Traceback" not in result.output


# ---------------------------------------------------------------------------
# NoFindingMatch: check was clear (may have cleared)
# ---------------------------------------------------------------------------


def test_no_match_when_check_clear_says_may_have_cleared(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    """No PRs returned (check ran and came up clean): user asked for pr:99 -> 'may have cleared'."""
    _stub_connectors(monkeypatch, tmp_path, prs=[])
    result = CliRunner().invoke(
        main, ["why", "pr:99"] + _BASE_ARGS
    )
    assert result.exit_code != 0
    assert "cleared" in result.output
    # Must NOT claim 'could not check': the check ran, it just returned nothing.
    assert "could not check" not in result.output


def test_no_match_when_check_clear_open_source_also_clears(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    _stub_connectors(monkeypatch, tmp_path, prs=[])
    result = CliRunner().invoke(
        main, ["open-source", "pr:99"] + _BASE_ARGS
    )
    assert result.exit_code != 0
    assert "cleared" in result.output
    assert "could not check" not in result.output


# ---------------------------------------------------------------------------
# NoFindingMatch: source was unreachable (could not check)
# ---------------------------------------------------------------------------


def test_no_match_when_unreachable_says_could_not_check(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    """No token -> conflict check is Unknown. Asking for pr:7 should say 'could not check',
    not 'may have cleared'. This is the key honest-UNKNOWN distinction."""

    monkeypatch.chdir(tmp_path)
    result = CliRunner().invoke(
        main,
        ["why", "pr:7"] + ["--github-repo", "acme/widgets", "--path", "src/app.py",
                             "--token-env", "TEAMCTX_DEFINITELY_UNSET_TOKEN"],
    )
    assert result.exit_code != 0
    assert "could not check" in result.output
    # Must NOT say 'cleared': we have no idea, the check never ran.
    assert "cleared" not in result.output


def test_no_match_when_unreachable_open_source_also_honest(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    monkeypatch.chdir(tmp_path)
    result = CliRunner().invoke(
        main,
        ["open-source", "pr:7"] + ["--github-repo", "acme/widgets", "--path", "src/app.py",
                                    "--token-env", "TEAMCTX_DEFINITELY_UNSET_TOKEN"],
    )
    assert result.exit_code != 0
    assert "could not check" in result.output
    assert "cleared" not in result.output


def test_no_match_path_selector_when_unreachable_says_could_not_check(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    """A `path:` selector spans the Conflict and Gate checks. With no token both are Unknown,
    so a no-match must say 'could not check', NOT 'may have cleared'. Without this, path: would
    fall through to a false all-clear (the gap this fix closes)."""

    monkeypatch.chdir(tmp_path)
    result = CliRunner().invoke(
        main,
        ["why", "path:src/app.py"] + ["--github-repo", "acme/widgets", "--path", "src/app.py",
                                       "--token-env", "TEAMCTX_DEFINITELY_UNSET_TOKEN"],
    )
    assert result.exit_code != 0
    assert "could not check" in result.output
    # Must NOT claim the finding cleared: neither the conflict nor the gate check ran.
    assert "cleared" not in result.output


# ---------------------------------------------------------------------------
# AmbiguousFinding: two findings match path:X
# ---------------------------------------------------------------------------


def test_ambiguous_path_exits_with_disambiguation(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    """Two PRs touch src/app.py: path:src/app.py is ambiguous; output names the specific
    selectors so the user can choose."""

    _stub_connectors(
        monkeypatch,
        tmp_path,
        prs=[
            _make_pr(7, paths=("src/app.py",)),
            _make_pr(8, paths=("src/app.py",)),
        ],
    )
    result = CliRunner().invoke(
        main, ["why", "path:src/app.py"] + _BASE_ARGS
    )
    assert result.exit_code != 0
    # Both specific selectors must be named in the message.
    assert "pr:7" in result.output
    assert "pr:8" in result.output


# ---------------------------------------------------------------------------
# Renderer unit tests
# ---------------------------------------------------------------------------


def _make_collision_card() -> object:
    """Build a realistic collision card via the real broker, from a forge_review signal."""

    from teamctx.connectors._contract import metadata_only_policy, source_status
    from teamctx.core.broker import broker_answer
    from teamctx.core.contracts import RequestContext, SourceSignal

    observed = "2026-01-01T00:00:00Z"
    repo = "acme/widgets"
    request = RequestContext(
        schema_version="teamctx.request_context.v0",
        request_id="t",
        repo=repo,
        branch="feature",
        task="work",
        paths=["src/app.py"],
        linked_issues=[],
        requested_at=observed,
        requesting_principal=None,
    )
    signal = SourceSignal(
        schema_version="teamctx.source_signal.v0",
        id="sig_github_pr_7_collision",
        signal_type="collision",
        source_family="git_hosting",
        scope={
            "repo": repo,
            "pr_number": 7,
            "state": "open",
            "url": "https://github.com/acme/widgets/pull/7",
            "files": ["src/app.py"],
        },
        evidence_summary="Open PR #7 changed src/app.py.",
        source_display="GitHub PR #7",
        freshness="fresh",
        confidence="high",
        visibility="visible",
        created_at=observed,
        observed_at=observed,
        expires_at="next_refresh",
        policy=metadata_only_policy("pr metadata"),
    )
    status = source_status(
        source_id="github_pr_metadata",
        source_family="git_hosting",
        scope={"repo": repo},
        status="fresh",
        observed_at=observed,
        safe_user_message="checked",
        visibility="silent",
        policy_reason="status only",
    )
    answer = broker_answer(request, [signal], [status])
    return answer.selection.cards[0]


def test_render_why_includes_finding_text() -> None:
    from teamctx.contract_render import render_why

    card = _make_collision_card()
    output = render_why(card)  # type: ignore[arg-type]
    assert "Open PR #7 changed src/app.py" in output


def test_render_why_includes_why_it_matters() -> None:
    from teamctx.contract_render import render_why

    card = _make_collision_card()
    output = render_why(card)  # type: ignore[arg-type]
    assert "Why it matters:" in output
    assert "editing" in output


def test_render_why_includes_flagged_reason() -> None:
    from teamctx.contract_render import render_why

    card = _make_collision_card()
    output = render_why(card)  # type: ignore[arg-type]
    assert "Why teamctx flagged it:" in output
    assert "same repository and file path" in output


def test_render_why_includes_source_with_freshness_and_confidence() -> None:
    from teamctx.contract_render import render_why

    card = _make_collision_card()
    output = render_why(card)  # type: ignore[arg-type]
    assert "GitHub PR #7" in output
    assert "fresh" in output
    assert "high confidence" in output


def test_render_why_includes_metadata_only_note_for_status_only() -> None:
    from teamctx.contract_render import render_why

    card = _make_collision_card()
    output = render_why(card)  # type: ignore[arg-type]
    assert "metadata only" in output
    assert "does not read the source body" in output


def test_render_why_has_no_em_dashes() -> None:
    from teamctx.contract_render import render_why

    card = _make_collision_card()
    output = render_why(card)  # type: ignore[arg-type]
    assert "—" not in output


def test_render_open_source_includes_gh_command() -> None:
    from teamctx.connectors._contract import metadata_only_policy
    from teamctx.contract_render import render_open_source
    from teamctx.core.contracts import SourceOpenTarget

    card = _make_collision_card()
    open_target = SourceOpenTarget(
        schema_version="teamctx.source_open_target.v0",
        id="open_github_pr_7",
        source_signal_id="sig_github_pr_7_collision",
        source_family="git_hosting",
        source_display="GitHub PR #7",
        open_label="Open PR",
        body_availability="status_only",
        policy=metadata_only_policy("pr metadata"),
    )
    output = render_open_source(card, (open_target,))  # type: ignore[arg-type]
    assert "gh pr view 7 --repo acme/widgets" in output


def test_render_open_source_includes_url() -> None:
    from teamctx.connectors._contract import metadata_only_policy
    from teamctx.contract_render import render_open_source
    from teamctx.core.contracts import SourceOpenTarget

    card = _make_collision_card()
    open_target = SourceOpenTarget(
        schema_version="teamctx.source_open_target.v0",
        id="open_github_pr_7",
        source_signal_id="sig_github_pr_7_collision",
        source_family="git_hosting",
        source_display="GitHub PR #7",
        open_label="Open PR",
        body_availability="status_only",
        policy=metadata_only_policy("pr metadata"),
    )
    output = render_open_source(card, (open_target,))  # type: ignore[arg-type]
    assert "https://github.com/acme/widgets/pull/7" in output


def test_render_open_source_notes_status_only_body() -> None:
    from teamctx.connectors._contract import metadata_only_policy
    from teamctx.contract_render import render_open_source
    from teamctx.core.contracts import SourceOpenTarget

    card = _make_collision_card()
    open_target = SourceOpenTarget(
        schema_version="teamctx.source_open_target.v0",
        id="open_github_pr_7",
        source_signal_id="sig_github_pr_7_collision",
        source_family="git_hosting",
        source_display="GitHub PR #7",
        open_label="Open PR",
        body_availability="status_only",
        policy=metadata_only_policy("pr metadata"),
    )
    output = render_open_source(card, (open_target,))  # type: ignore[arg-type]
    assert "metadata only" in output
    assert "status-only by policy" in output


def test_render_open_source_falls_back_to_card_source_body_when_no_target() -> None:
    """When there is no matching SourceOpenTarget, card.source_body is the fallback."""

    from teamctx.contract_render import render_open_source

    card = _make_collision_card()
    output = render_open_source(card, ())  # type: ignore[arg-type]
    # card.source_body == 'status_only' -> metadata-only note still appears
    assert "metadata only" in output


def test_render_open_source_has_no_em_dashes() -> None:
    from teamctx.connectors._contract import metadata_only_policy
    from teamctx.contract_render import render_open_source
    from teamctx.core.contracts import SourceOpenTarget

    card = _make_collision_card()
    open_target = SourceOpenTarget(
        schema_version="teamctx.source_open_target.v0",
        id="open_github_pr_7",
        source_signal_id="sig_github_pr_7_collision",
        source_family="git_hosting",
        source_display="GitHub PR #7",
        open_label="Open PR",
        body_availability="status_only",
        policy=metadata_only_policy("pr metadata"),
    )
    output = render_open_source(card, (open_target,))  # type: ignore[arg-type]
    assert "—" not in output
