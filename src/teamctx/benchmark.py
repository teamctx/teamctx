"""Benchmark prompt export helpers."""

from __future__ import annotations

import csv
import json
from dataclasses import dataclass
from pathlib import Path

from teamctx.context import agent_prompt_cards
from teamctx.fixtures import load_fixture
from teamctx.render import render_baseline_prompt, render_benchmark_prompt


@dataclass(frozen=True)
class BenchmarkExport:
    fixture_id: str
    baseline_path: Path
    context_path: Path
    first_prompt: str


def benchmark_fixture_paths(fixtures_dir: Path) -> list[Path]:
    return sorted(path for path in fixtures_dir.glob("*.json") if path.is_file())


def export_benchmark_pack(fixtures_dir: Path, output_dir: Path) -> list[BenchmarkExport]:
    paths = benchmark_fixture_paths(fixtures_dir)
    if not paths:
        raise ValueError(f"No benchmark fixture JSON files found in {fixtures_dir}")

    output_dir.mkdir(parents=True, exist_ok=True)
    exports: list[BenchmarkExport] = []

    for index, path in enumerate(paths, start=1):
        fixture = load_fixture(path)
        cards = agent_prompt_cards(fixture)
        prefix = f"{index:02d}-{fixture.fixture_id}"
        baseline_path = output_dir / f"{prefix}-baseline.txt"
        context_path = output_dir / f"{prefix}-context.txt"
        baseline_path.write_text(render_baseline_prompt(fixture), encoding="utf-8")
        context_path.write_text(render_benchmark_prompt(fixture, cards), encoding="utf-8")
        exports.append(
            BenchmarkExport(
                fixture_id=fixture.fixture_id,
                baseline_path=baseline_path,
                context_path=context_path,
                first_prompt="baseline" if index % 2 else "context",
            )
        )

    (output_dir / "run-sheet.md").write_text(_render_run_sheet(exports), encoding="utf-8")
    (output_dir / "run-order.md").write_text(_render_run_order(exports), encoding="utf-8")
    (output_dir / "manifest.json").write_text(_render_manifest(exports), encoding="utf-8")
    _write_score_sheet(output_dir / "score-sheet.csv", exports)
    _write_response_readme(output_dir / "responses" / "README.md", exports)
    _write_results_readme(output_dir / "results" / "README.md")
    return exports


def _render_run_sheet(exports: list[BenchmarkExport]) -> str:
    lines = [
        "# Benchmark Run Sheet",
        "",
        "Use each prompt in a fresh model session. Score only after both prompts "
        "for a scenario are collected.",
        "",
        "| Scenario | Baseline prompt | Context prompt | First prompt | Score | Notes |",
        "| --- | --- | --- | --- | ---: | --- |",
    ]
    for export in exports:
        baseline = export.baseline_path.name
        context = export.context_path.name
        lines.append(
            f"| `{export.fixture_id}` | `{baseline}` | `{context}` | "
            f"{export.first_prompt} |  |  |"
        )
    lines.extend(
        [
            "",
            "Score:",
            "",
            "- `+2`: context clearly prevents a likely error or materially improves "
            "the next action.",
            "- `+1`: context adds useful caution or verification without much extra friction.",
            "- `0`: no meaningful difference.",
            "- `-1`: context adds friction, vague caveats, or unnecessary user burden.",
            "- `-2`: context causes over-trust, invented facts, unsafe behavior, or wrong scope.",
        ]
    )
    return "\n".join(lines) + "\n"


def _render_run_order(exports: list[BenchmarkExport]) -> str:
    lines = [
        "# Benchmark Run Order",
        "",
        "Run each prompt in a fresh model session. Do not score until both prompts "
        "for a scenario are complete.",
        "",
    ]
    for index, export in enumerate(exports, start=1):
        first = export.baseline_path if export.first_prompt == "baseline" else export.context_path
        second = export.context_path if export.first_prompt == "baseline" else export.baseline_path
        lines.extend(
            [
                f"## {index}. {export.fixture_id}",
                "",
                f"1. `{first.name}`",
                f"2. `{second.name}`",
                "",
            ]
        )
    return "\n".join(lines).rstrip() + "\n"


def _render_manifest(exports: list[BenchmarkExport]) -> str:
    manifest = {
        "version": 1,
        "scenarios": [
            {
                "fixture_id": export.fixture_id,
                "baseline_prompt": export.baseline_path.name,
                "context_prompt": export.context_path.name,
                "first_prompt": export.first_prompt,
            }
            for export in exports
        ],
    }
    return json.dumps(manifest, indent=2) + "\n"


def _write_score_sheet(path: Path, exports: list[BenchmarkExport]) -> None:
    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.writer(handle, lineterminator="\n")
        writer.writerow(
            [
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
            ]
        )
        for export in exports:
            writer.writerow(
                [
                    export.fixture_id,
                    "",
                    f"responses/MODEL/{export.fixture_id}-baseline.md",
                    f"responses/MODEL/{export.fixture_id}-context.md",
                    "",
                    "",
                    "",
                    "",
                    "",
                    "",
                ]
            )


def _write_response_readme(path: Path, exports: list[BenchmarkExport]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    lines = [
        "# Benchmark Responses",
        "",
        "Store raw model outputs here. Use one directory per model and keep the "
        "prompt variant in the filename.",
        "",
        "Naming:",
        "",
        "- `responses/{model}/{fixture_id}-baseline.md`",
        "- `responses/{model}/{fixture_id}-context.md`",
        "",
        "Expected files:",
        "",
    ]
    for export in exports:
        lines.extend(
            [
                f"- `responses/MODEL/{export.fixture_id}-baseline.md`",
                f"- `responses/MODEL/{export.fixture_id}-context.md`",
            ]
        )
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def _write_results_readme(path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        "\n".join(
            [
                "# Benchmark Results",
                "",
                "Fill `score-sheet.csv` after both answers for a scenario are captured.",
                "",
                "Scoring:",
                "",
                "- `+2`: context clearly prevents a likely error or materially "
                "improves the next action.",
                "- `+1`: context adds useful caution or verification without "
                "much extra friction.",
                "- `0`: no meaningful difference.",
                "- `-1`: context adds friction, vague caveats, or unnecessary user burden.",
                "- `-2`: context causes over-trust, invented facts, unsafe "
                "behavior, or wrong scope.",
                "",
                "Flags:",
                "",
                "- `over_trust`: answer treats context as truth beyond the evidence provided.",
                "- `language_confusion`: answer exposes product-internal terms to the user.",
                "- `token_waste`: answer spends more attention than the task warrants.",
                "- `lookup_saved`: answer avoids likely repo or tracker lookup work.",
            ]
        )
        + "\n",
        encoding="utf-8",
    )
