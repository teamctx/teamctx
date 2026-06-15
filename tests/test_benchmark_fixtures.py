from __future__ import annotations

import csv
import json
from pathlib import Path

from click.testing import CliRunner

from teamctx.benchmark import export_benchmark_pack
from teamctx.cli import main
from teamctx.context import agent_prompt_cards, context_cards
from teamctx.core.fixtures import load_fixture
from teamctx.core.models import Fixture
from teamctx.render import render_baseline_prompt, render_benchmark_prompt

ROOT = Path(__file__).resolve().parent.parent
BENCHMARK_FIXTURES = ROOT / "docs/product/discovery/fixtures/benchmark/primary"
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


def benchmark_fixture_paths() -> list[Path]:
    return sorted(BENCHMARK_FIXTURES.glob("primary-*.json"))


def load_primary_fixture(fixture_id: str) -> Fixture:
    return load_fixture(BENCHMARK_FIXTURES / f"{fixture_id}.json")


def test_primary_benchmark_fixture_count() -> None:
    assert len(benchmark_fixture_paths()) == 6


def test_primary_benchmark_fixtures_load_and_generate_prompts() -> None:
    for path in benchmark_fixture_paths():
        fixture = load_fixture(path)
        cards = agent_prompt_cards(fixture)
        baseline = render_baseline_prompt(fixture)
        context = render_benchmark_prompt(fixture, cards)
        card_ids = {card.id for card in cards}

        assert fixture.expected_cards
        assert "Working context" not in baseline
        assert (
            "Proceed normally. Ask only if you need information that is not available."
            in baseline
        )
        assert "Working context" in context
        assert "Treat source-backed items as evidence" in context
        for card in fixture.expected_cards:
            if card.id in card_ids:
                assert card.text in context
            else:
                assert card.text not in context


def test_agent_prompt_gating_separates_action_context_from_source_health() -> None:
    expected_prompt_cards = {
        "primary-01-overlapping-file-change-v1": ["card_pr_collision"],
        "primary-02-changed-acceptance-criteria-v1": ["card_issue_changed"],
        "primary-03-stale-process-doc-v1": [],
        "primary-04-safety-blocked-source-change-v1": [],
        "primary-05-inaccessible-linked-docs-v1": [],
        "primary-06-project-guidance-applies-v1": ["card_project_guidance"],
    }

    for fixture_id, expected_ids in expected_prompt_cards.items():
        fixture = load_primary_fixture(fixture_id)
        assert [card.id for card in agent_prompt_cards(fixture)] == expected_ids


def test_source_health_cards_still_exist_in_rich_context() -> None:
    for fixture_id in (
        "primary-03-stale-process-doc-v1",
        "primary-04-safety-blocked-source-change-v1",
        "primary-05-inaccessible-linked-docs-v1",
    ):
        fixture = load_primary_fixture(fixture_id)

        assert agent_prompt_cards(fixture) == []
        assert [card.id for card in context_cards(fixture)] == [fixture.expected_cards[0].id]


def test_explicit_selection_can_include_source_health_card_in_agent_prompt() -> None:
    fixture = load_primary_fixture("primary-03-stale-process-doc-v1")

    cards = agent_prompt_cards(fixture, selected_card_ids=("card_stale_docs",))

    assert [card.id for card in cards] == ["card_stale_docs"]


def test_primary_benchmark_prompts_avoid_banned_terms() -> None:
    for path in benchmark_fixture_paths():
        fixture = load_fixture(path)
        prompts = [
            render_baseline_prompt(fixture),
            render_benchmark_prompt(fixture, agent_prompt_cards(fixture)),
        ]
        for prompt in prompts:
            lower = prompt.lower()
            for term in BANNED_TERMS:
                assert term not in lower, f"{path.name} generated banned term: {term}"


def test_cli_benchmark_prompt_accepts_fixture_id_without_hard_coded_scenario() -> None:
    runner = CliRunner()
    path = BENCHMARK_FIXTURES / "primary-01-overlapping-file-change-v1.json"

    result = runner.invoke(
        main, ["benchmark-prompt", "--variant", "context", "--fixture", str(path)]
    )

    assert result.exit_code == 0
    assert "Another open PR changed src/auth/token.py 11 minutes ago." in result.output


def test_cli_benchmark_prompt_omits_source_health_by_default() -> None:
    runner = CliRunner()
    path = BENCHMARK_FIXTURES / "primary-03-stale-process-doc-v1.json"

    result = runner.invoke(
        main, ["benchmark-prompt", "--variant", "context", "--fixture", str(path)]
    )

    assert result.exit_code == 0
    assert "No working context for this task." in result.output
    assert "The release checklist source is stale." not in result.output


def test_cli_benchmark_prompt_rejects_mismatched_scenario() -> None:
    runner = CliRunner()
    path = BENCHMARK_FIXTURES / "primary-01-overlapping-file-change-v1.json"

    result = runner.invoke(
        main,
        [
            "benchmark-prompt",
            "--scenario",
            "not-this-fixture",
            "--variant",
            "context",
            "--fixture",
            str(path),
        ],
    )

    assert result.exit_code != 0
    assert "does not match fixture" in result.output


def test_export_benchmark_pack_writes_prompt_files_and_run_sheet(tmp_path: Path) -> None:
    exports = export_benchmark_pack(BENCHMARK_FIXTURES, tmp_path)

    assert len(exports) == 6
    assert len(list(tmp_path.glob("*-baseline.txt"))) == 6
    assert len(list(tmp_path.glob("*-context.txt"))) == 6
    assert (tmp_path / "run-sheet.md").exists()
    assert (tmp_path / "run-order.md").exists()
    assert (tmp_path / "manifest.json").exists()
    assert (tmp_path / "score-sheet.csv").exists()
    assert (tmp_path / "responses" / "README.md").exists()
    assert (tmp_path / "results" / "README.md").exists()

    first = exports[0]
    fixture = load_fixture(BENCHMARK_FIXTURES / f"{first.fixture_id}.json")
    assert first.baseline_path.read_text(encoding="utf-8") == render_baseline_prompt(fixture)
    assert first.context_path.read_text(encoding="utf-8") == render_benchmark_prompt(
        fixture, agent_prompt_cards(fixture)
    )


def test_cli_benchmark_export_writes_prompt_pack(tmp_path: Path) -> None:
    runner = CliRunner()

    result = runner.invoke(
        main,
        [
            "benchmark-export",
            "--fixtures-dir",
            str(BENCHMARK_FIXTURES),
            "--output-dir",
            str(tmp_path),
        ],
    )

    assert result.exit_code == 0
    assert "Exported 6 benchmark scenarios" in result.output
    assert (tmp_path / "run-sheet.md").exists()
    assert (tmp_path / "responses" / "README.md").exists()


def test_export_benchmark_pack_writes_manifest_run_order_and_score_sheet(tmp_path: Path) -> None:
    exports = export_benchmark_pack(BENCHMARK_FIXTURES, tmp_path)
    manifest = json.loads((tmp_path / "manifest.json").read_text(encoding="utf-8"))
    run_order = (tmp_path / "run-order.md").read_text(encoding="utf-8")

    assert manifest["version"] == 1
    assert len(manifest["scenarios"]) == 6
    assert manifest["scenarios"][0]["first_prompt"] == "baseline"
    assert manifest["scenarios"][1]["first_prompt"] == "context"
    assert "01-primary-01-overlapping-file-change-v1-baseline.txt" in run_order
    assert "02-primary-02-changed-acceptance-criteria-v1-context.txt" in run_order

    with (tmp_path / "score-sheet.csv").open(newline="", encoding="utf-8") as handle:
        rows = list(csv.DictReader(handle))

    assert [row["fixture_id"] for row in rows] == [export.fixture_id for export in exports]
    assert set(rows[0]) == {
        "fixture_id",
        "model",
        "baseline_response_file",
        "context_response_file",
        "score",
        "over_trust",
        "language_confusion",
        "token_waste",
        "lookup_saved",
        "notes",
    }
    assert rows[0]["baseline_response_file"] == (
        "responses/MODEL/primary-01-overlapping-file-change-v1-baseline.md"
    )
    assert rows[0]["context_response_file"] == (
        "responses/MODEL/primary-01-overlapping-file-change-v1-context.md"
    )
