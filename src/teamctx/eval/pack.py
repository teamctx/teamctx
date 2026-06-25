"""Export an A/B trial pack from scenarios, through the real engine.

For each scenario it writes a baseline prompt and a context prompt (the latter built from
``broker_answer``), plus a manifest and a score sheet for recording results. This is the
lean evidence core: enough to run a deconfounded A/B by hand or with a driver, with the
context arm guaranteed to be the live product output. The heavy disposable-repo campaign
runner is intentionally not here (it is the study, not the foundation).
"""

from __future__ import annotations

import csv
import json
from dataclasses import dataclass
from pathlib import Path

from teamctx.eval.prompts import render_baseline_prompt, render_context_prompt
from teamctx.eval.scenario import EvalScenario, load_scenario, scenario_paths


@dataclass(frozen=True)
class ScenarioExport:
    scenario_id: str
    baseline_path: Path
    context_path: Path
    first_prompt: str  # which arm is shown first (alternates, to debias ordering)


def export_eval_pack(scenarios_dir: Path, output_dir: Path) -> list[ScenarioExport]:
    paths = scenario_paths(scenarios_dir)
    if not paths:
        raise ValueError(f"No scenario JSON files found in {scenarios_dir}")

    output_dir.mkdir(parents=True, exist_ok=True)
    exports: list[ScenarioExport] = []
    for index, path in enumerate(paths, start=1):
        scenario = load_scenario(path)
        prefix = f"{index:02d}-{scenario.scenario_id}"
        baseline_path = output_dir / f"{prefix}-baseline.txt"
        context_path = output_dir / f"{prefix}-context.txt"
        baseline_path.write_text(render_baseline_prompt(scenario), encoding="utf-8")
        context_path.write_text(render_context_prompt(scenario), encoding="utf-8")
        exports.append(
            ScenarioExport(
                scenario_id=scenario.scenario_id,
                baseline_path=baseline_path,
                context_path=context_path,
                first_prompt="baseline" if index % 2 else "context",
            )
        )

    (output_dir / "manifest.json").write_text(_render_manifest(exports), encoding="utf-8")
    _write_score_sheet(output_dir / "score-sheet.csv", exports)
    return exports


def run_one_scenario(scenario: EvalScenario, *, variant: str) -> str:
    """The minimal runner: produce the exact prompt an agent would receive for one arm.
    ``variant`` is 'baseline' or 'context'. This is the end-to-end wiring — scenario through
    the real engine to a prompt — without spawning an agent (that is the campaign)."""

    if variant == "baseline":
        return render_baseline_prompt(scenario)
    if variant == "context":
        return render_context_prompt(scenario)
    raise ValueError(f"unknown variant: {variant!r}")


def _render_manifest(exports: list[ScenarioExport]) -> str:
    payload = {
        "scenarios": [
            {
                "scenario_id": export.scenario_id,
                "baseline": export.baseline_path.name,
                "context": export.context_path.name,
                "first_prompt": export.first_prompt,
            }
            for export in exports
        ]
    }
    return json.dumps(payload, indent=2, sort_keys=True) + "\n"


def _write_score_sheet(path: Path, exports: list[ScenarioExport]) -> None:
    with path.open("w", encoding="utf-8", newline="\n") as handle:
        writer = csv.writer(handle, lineterminator="\n")
        writer.writerow(["scenario_id", "arm", "first_prompt", "outcome", "notes"])
        for export in exports:
            writer.writerow([export.scenario_id, "baseline", export.first_prompt, "", ""])
            writer.writerow([export.scenario_id, "context", export.first_prompt, "", ""])
