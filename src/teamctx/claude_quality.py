"""Quality assessment for Claude agent benchmark runs."""

from __future__ import annotations

import csv
import json
import re
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any, Literal

from teamctx.core.fixtures import load_fixture
from teamctx.core.models import Fixture

QualityLevel = Literal["pass", "review", "fail"]

_RESULT_KEY_RE = re.compile(r"^([a-zA-Z_]+):\s*(.*)$")
_DIFF_FILE_RE = re.compile(r"^diff --git a/(.*?) b/(.*?)$")


@dataclass(frozen=True)
class ClaudeQualityAssessment:
    fixture_id: str
    model: str
    variant: str
    run_dir: str
    quality_level: QualityLevel
    quality_score: int
    max_quality_score: int
    risk_noticed: str
    lookup_saved: str
    blocked: str
    result_block_present: bool
    changed_files: list[str]
    target_files_touched: list[str]
    source_snapshots_touched: bool
    tests_touched: bool
    validation_attempted: bool
    retry_behavior_added: bool
    preserves_existing_api: str
    notes: list[str]


def assess_claude_run(fixture: Fixture, run_dir: Path) -> ClaudeQualityAssessment:
    metrics = _read_json(run_dir / "metrics.json")
    diff_text = (run_dir / "workspace.diff").read_text(encoding="utf-8")
    result_text = extract_final_result_text((run_dir / "stream.jsonl").read_text(encoding="utf-8"))
    result_block = parse_agent_result_block(result_text)

    changed_files = changed_files_from_diff(diff_text)
    target_files = [str(item) for item in fixture.scope.get("files", [])]
    target_files_touched = [path for path in target_files if path in changed_files]
    source_snapshots_touched = any(path.startswith("source-snapshots/") for path in changed_files)
    tests_touched = any(path.startswith("tests/") for path in changed_files)
    tool_names = _dict_field(metrics.get("tool_names"))
    validation_attempted = tests_touched or int(tool_names.get("Bash", 0)) > 0
    retry_behavior_added = diff_adds_retry_behavior(diff_text)
    preserves_existing_api = api_preservation_for_fixture(fixture, diff_text)

    notes: list[str] = []
    score = 0
    max_score = 7

    if not bool(metrics.get("is_error", True)) and int(metrics.get("exit_code") or 0) == 0:
        score += 1
    else:
        notes.append("run did not complete cleanly")

    if target_files_touched:
        score += 1
    else:
        notes.append("target file was not changed")

    if not source_snapshots_touched:
        score += 1
    else:
        notes.append("source snapshots were modified")

    if result_block:
        score += 1
    else:
        notes.append("final benchmark result block missing")

    risk_noticed = result_block.get("risk_noticed", "missing")
    if risk_noticed == "yes":
        score += 1
    else:
        notes.append("risk was not marked as noticed")

    if retry_behavior_added:
        score += 1
    else:
        notes.append("diff does not appear to add retry behavior")

    if validation_attempted:
        score += 1
    else:
        notes.append("no validation command or test change captured")

    if preserves_existing_api != "n/a":
        max_score += 1
        if preserves_existing_api == "yes":
            score += 1
        else:
            notes.append("changed existing rotate_token API in collision scenario")

    critical_failure = (
        bool(metrics.get("is_error", True))
        or not target_files_touched
        or source_snapshots_touched
        or result_block.get("blocked") == "yes"
    )
    if critical_failure:
        quality_level: QualityLevel = "fail"
    elif notes:
        quality_level = "review"
    else:
        quality_level = "pass"

    return ClaudeQualityAssessment(
        fixture_id=str(metrics.get("fixture_id") or fixture.fixture_id),
        model=str(metrics.get("model") or ""),
        variant=str(metrics.get("variant") or ""),
        run_dir=run_dir.name,
        quality_level=quality_level,
        quality_score=score,
        max_quality_score=max_score,
        risk_noticed=risk_noticed,
        lookup_saved=result_block.get("lookup_saved", "missing"),
        blocked=result_block.get("blocked", "missing"),
        result_block_present=bool(result_block),
        changed_files=changed_files,
        target_files_touched=target_files_touched,
        source_snapshots_touched=source_snapshots_touched,
        tests_touched=tests_touched,
        validation_attempted=validation_attempted,
        retry_behavior_added=retry_behavior_added,
        preserves_existing_api=preserves_existing_api,
        notes=notes,
    )


def assess_claude_run_dir(fixtures_dir: Path, run_root: Path) -> list[ClaudeQualityAssessment]:
    fixtures: dict[str, Fixture] = {}
    for path in fixtures_dir.glob("*.json"):
        fixture = load_fixture(path)
        fixtures[fixture.fixture_id] = fixture
    assessments: list[ClaudeQualityAssessment] = []
    for metrics_path in sorted(run_root.glob("*/metrics.json")):
        metrics = _read_json(metrics_path)
        fixture_id = str(metrics.get("fixture_id") or "")
        matched_fixture = fixtures.get(fixture_id)
        if matched_fixture is None:
            continue
        assessments.append(assess_claude_run(matched_fixture, metrics_path.parent))
    write_quality_summary(run_root / "quality.csv", assessments)
    write_quality_markdown(run_root / "quality.md", assessments)
    return assessments


def parse_agent_result_block(text: str) -> dict[str, str]:
    marker = "AGENT_BENCHMARK_RESULT"
    if marker not in text:
        return {}
    _, after = text.split(marker, 1)
    result: dict[str, str] = {}
    for raw_line in after.splitlines():
        line = raw_line.strip()
        if not line:
            continue
        match = _RESULT_KEY_RE.match(line)
        if not match:
            continue
        key = match.group(1).lower()
        result[key] = match.group(2).strip().lower()
    return result


def extract_final_result_text(stream_text: str) -> str:
    result = ""
    for line in stream_text.splitlines():
        if not line.strip():
            continue
        try:
            event = json.loads(line)
        except json.JSONDecodeError:
            continue
        if event.get("type") == "result":
            result = str(event.get("result") or "")
    return result


def changed_files_from_diff(diff_text: str) -> list[str]:
    files: list[str] = []
    for line in diff_text.splitlines():
        match = _DIFF_FILE_RE.match(line)
        if match:
            files.append(match.group(2))
    return files


def diff_adds_retry_behavior(diff_text: str) -> bool:
    added_lines = [line[1:].lower() for line in diff_text.splitlines() if _is_added_line(line)]
    added = "\n".join(added_lines)
    return "retry" in added and ("rotate_token" in added or "tokenrotationerror" in added)


def api_preservation_for_fixture(fixture: Fixture, diff_text: str) -> str:
    if fixture.fixture_id != "primary-01-overlapping-file-change-v1":
        return "n/a"
    removed_original = "-def rotate_token(client: object, token: str) -> str:" in diff_text
    changed_signature = "+def rotate_token(client: object, token: str," in diff_text
    return "no" if removed_original or changed_signature else "yes"


def write_quality_summary(path: Path, assessments: list[ClaudeQualityAssessment]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(
            handle,
            fieldnames=[
                "fixture_id",
                "model",
                "variant",
                "run_dir",
                "quality_level",
                "quality_score",
                "max_quality_score",
                "risk_noticed",
                "lookup_saved",
                "blocked",
                "result_block_present",
                "changed_files",
                "target_files_touched",
                "source_snapshots_touched",
                "tests_touched",
                "validation_attempted",
                "retry_behavior_added",
                "preserves_existing_api",
                "notes",
            ],
            lineterminator="\n",
        )
        writer.writeheader()
        for assessment in assessments:
            data = asdict(assessment)
            data["changed_files"] = json.dumps(assessment.changed_files)
            data["target_files_touched"] = json.dumps(assessment.target_files_touched)
            data["notes"] = " | ".join(assessment.notes)
            writer.writerow(data)


def write_quality_markdown(path: Path, assessments: list[ClaudeQualityAssessment]) -> None:
    lines = [
        "# Claude Agent Quality Summary",
        "",
        "| Fixture | Model | Variant | Level | Score | Risk noticed | API preserved | Notes |",
        "| --- | --- | --- | --- | ---: | --- | --- | --- |",
    ]
    for assessment in assessments:
        notes = "; ".join(assessment.notes) if assessment.notes else ""
        lines.append(
            f"| `{assessment.fixture_id}` | `{assessment.model}` | {assessment.variant} | "
            f"{assessment.quality_level} | "
            f"{assessment.quality_score}/{assessment.max_quality_score} | "
            f"{assessment.risk_noticed} | {assessment.preserves_existing_api} | {notes} |"
        )
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def _read_json(path: Path) -> dict[str, Any]:
    data = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(data, dict):
        raise ValueError(f"Expected JSON object in {path}")
    return data


def _dict_field(value: object) -> dict[str, int]:
    if not isinstance(value, dict):
        return {}
    result: dict[str, int] = {}
    for key, item in value.items():
        if isinstance(key, str) and isinstance(item, int):
            result[key] = item
    return result


def _is_added_line(line: str) -> bool:
    return line.startswith("+") and not line.startswith("+++")
