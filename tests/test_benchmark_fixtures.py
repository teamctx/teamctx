from __future__ import annotations

import csv
import json
from pathlib import Path

from click.testing import CliRunner

from teamctx.benchmark import export_benchmark_pack
from teamctx.cli import main
from teamctx.context import context_cards
from teamctx.core.fixtures import load_fixture
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


def test_primary_benchmark_fixture_count() -> None:
    assert len(benchmark_fixture_paths()) == 6


def test_primary_benchmark_fixtures_load_and_generate_prompts() -> None:
    for path in benchmark_fixture_paths():
        fixture = load_fixture(path)
        cards = context_cards(fixture)
        baseline = render_baseline_prompt(fixture)
        context = render_benchmark_prompt(fixture, cards)

        assert fixture.expected_cards
        assert "Working context" not in baseline
        assert (
            "Proceed normally. Ask only if you need information that is not available."
            in baseline
        )
        assert "Working context" in context
        assert "Treat source-backed items as evidence" in context
        for card in fixture.expected_cards:
            if card.default_agent_visible and card.relevance is None:
                assert card.text in context


def test_primary_benchmark_prompts_avoid_banned_terms() -> None:
    for path in benchmark_fixture_paths():
        fixture = load_fixture(path)
        prompts = [
            render_baseline_prompt(fixture),
            render_benchmark_prompt(fixture, context_cards(fixture)),
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
        fixture, context_cards(fixture)
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
