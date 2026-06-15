from __future__ import annotations

from pathlib import Path

from click.testing import CliRunner

from teamctx.cli import main
from teamctx.context import agent_prompt_cards, context_cards
from teamctx.core.fixtures import load_fixture
from teamctx.render import render_benchmark_prompt, render_context_cards
from teamctx.session import add_card_to_session, read_session
from teamctx.why import render_why

ROOT = Path(__file__).resolve().parent.parent
FIXTURE = ROOT / "docs/product/discovery/fixtures/vertical-slice/auth-token-retry-v1.json"
GOLDEN = ROOT / "docs/product/discovery/fixtures/vertical-slice/golden"
BANNED_TERMS = (
    "memory",
    "ledger",
    "registry",
    "promotion",
    "quarantine",
    "source signal",
    "advisory match",
    "authority tier",
    "normalized artifact",
    "durable core",
)


def golden(name: str) -> str:
    return (GOLDEN / name).read_text(encoding="utf-8")


def test_fixture_loads_and_validates() -> None:
    fixture = load_fixture(FIXTURE)

    assert fixture.fixture_id == "auth-token-retry-v1"
    assert fixture.expected_cards[0].id == "card_pr_collision"


def test_default_context_matches_golden() -> None:
    fixture = load_fixture(FIXTURE)

    assert render_context_cards(context_cards(fixture)) == golden("context-default.txt")


def test_release_scoped_stale_source_matches_golden() -> None:
    fixture = load_fixture(FIXTURE)
    cards = context_cards(
        fixture,
        include_default=False,
        relevance_tags=("release_task_only",),
    )

    assert render_context_cards(cards) == golden("context-release-stale-source.txt")


def test_show_why_matches_golden() -> None:
    fixture = load_fixture(FIXTURE)

    assert render_why(fixture, "card_pr_collision") == golden("why-card-pr-collision.txt")


def test_session_use_includes_advisory_note(tmp_path: Path) -> None:
    fixture = load_fixture(FIXTURE)
    add_card_to_session("demo", "card_auth_notes_advisory", root=tmp_path)
    selected = read_session("demo", root=tmp_path).card_ids

    assert render_context_cards(context_cards(fixture, selected_card_ids=selected)) == golden(
        "context-after-use-advisory-note.txt"
    )


def test_benchmark_prompt_matches_golden() -> None:
    fixture = load_fixture(FIXTURE)

    assert render_benchmark_prompt(fixture, agent_prompt_cards(fixture)) == golden(
        "benchmark-context-prompt.txt"
    )


def test_cli_context_matches_golden() -> None:
    runner = CliRunner()

    result = runner.invoke(main, ["context", "--fixture", str(FIXTURE)])

    assert result.exit_code == 0
    assert result.output == golden("context-default.txt")


def test_golden_outputs_avoid_banned_user_facing_terms() -> None:
    for path in GOLDEN.glob("*.txt"):
        text = path.read_text(encoding="utf-8").lower()
        for term in BANNED_TERMS:
            assert term not in text, f"{path.name} contains banned term: {term}"
