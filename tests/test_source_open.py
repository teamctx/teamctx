from __future__ import annotations

from pathlib import Path

from click.testing import CliRunner

from teamctx.cli import main
from teamctx.core.fixtures import load_fixture
from teamctx.core.models import Fixture
from teamctx.source_open import SourceOpenError, render_open_source

ROOT = Path(__file__).resolve().parent.parent
VERTICAL_FIXTURE = ROOT / "docs/product/discovery/fixtures/vertical-slice/auth-token-retry-v1.json"


def test_open_source_card_renders_allowed_source_body() -> None:
    fixture = load_fixture(VERTICAL_FIXTURE)

    output = render_open_source(fixture, "card_pr_collision")

    assert output == (
        "Open source\n"
        "\n"
        "GitHub PR #482\n"
        "Freshness: fresh\n"
        "\n"
        "GitHub PR #482\n"
        "\n"
        "Summary: add retry handling for token rotation when the upstream client times out.\n"
        "Files touched: src/auth/token.py.\n"
        "Review note: keep legacy client behavior unchanged.\n"
    )


def test_open_source_accepts_source_id() -> None:
    fixture = load_fixture(VERTICAL_FIXTURE)

    output = render_open_source(fixture, "sig_pr_482_collision")

    assert "Summary: add retry handling" in output


def test_open_source_policy_denial_keeps_status_but_not_body() -> None:
    fixture = load_fixture(VERTICAL_FIXTURE)

    output = render_open_source(fixture, "card_stale_docs")

    assert "Confluence Release Checklist" in output
    assert "Freshness: stale" in output
    assert "Use as background only. Verify before relying." in output
    assert "Source body unavailable." in output
    assert "TeamCtx can show the status, but not the source body." in output


def test_open_source_does_not_leak_blocked_artifact_body() -> None:
    fixture = Fixture.model_validate(
        {
            "fixture_id": "blocked-source-body-v1",
            "date": "2026-06-16",
            "task": "Do the linked work.",
            "source_signals": [
                {
                    "id": "sig_blocked",
                    "signal_type": "blocked_source",
                    "source_family": "issue_tracker",
                    "scope": {},
                    "evidence_summary": "Part of the issue was blocked by policy.",
                    "source_display": "Jira API-482",
                    "freshness": "blocked",
                    "confidence": "high",
                    "visibility": "warning_only",
                    "created_at": "2026-06-16T00:00:00Z",
                    "observed_at": "2026-06-16T00:00:00Z",
                    "expires_at": "2026-06-16T01:00:00Z",
                    "policy": {
                        "can_render_to_user": True,
                        "can_render_to_agent": True,
                        "can_include_source_text": True,
                        "requires_review_for_guidance": False,
                    },
                }
            ],
            "source_artifacts": [
                {
                    "id": "artifact_blocked",
                    "source_signal_id": "sig_blocked",
                    "title": "Jira API-482",
                    "body": "DO NOT LEAK: blocked source body",
                }
            ],
            "guidance_records": [],
            "expected_cards": [
                {
                    "id": "card_blocked",
                    "section": "Needs attention",
                    "text": "Part of the issue was blocked by policy.",
                    "why_this_matters": "unknown work may be unsafe.",
                    "source": "Jira API-482",
                    "refs": ["sig_blocked"],
                }
            ],
        }
    )

    output = render_open_source(fixture, "card_blocked")

    assert "Source body unavailable." in output
    assert "This source is blocked by policy." in output
    assert "DO NOT LEAK" not in output


def test_open_source_unknown_id_raises_clear_error() -> None:
    fixture = load_fixture(VERTICAL_FIXTURE)

    try:
        render_open_source(fixture, "not-real")
    except SourceOpenError as exc:
        assert str(exc) == "Unknown source or card id: not-real"
    else:
        raise AssertionError("expected SourceOpenError")


def test_cli_open_source_renders_allowed_source_body() -> None:
    runner = CliRunner()

    result = runner.invoke(
        main, ["open-source", "card_pr_collision", "--fixture", str(VERTICAL_FIXTURE)]
    )

    assert result.exit_code == 0
    assert "Open source" in result.output
    assert "Summary: add retry handling" in result.output
