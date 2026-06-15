from __future__ import annotations

import csv
import json
from pathlib import Path

from teamctx.claude_quality import (
    assess_claude_run,
    changed_files_from_diff,
    diff_adds_retry_behavior,
    extract_final_result_text,
    parse_agent_result_block,
    write_quality_summary,
)
from teamctx.core.fixtures import load_fixture

ROOT = Path(__file__).resolve().parent.parent
FIXTURE_PATH = (
    ROOT
    / "docs/product/discovery/fixtures/benchmark/primary/primary-01-overlapping-file-change-v1.json"
)

BASELINE_DIFF = """diff --git a/src/auth/token.py b/src/auth/token.py
index 49c8881..2819f0d 100644
--- a/src/auth/token.py
+++ b/src/auth/token.py
@@ -21,3 +21,12 @@ def rotate_token(client: object, token: str) -> str:
+
+
+def rotate_token_with_retry(client: object, token: str) -> str:
+    return rotate_token(client, token)
"""

CONTEXT_DIFF = """diff --git a/src/auth/token.py b/src/auth/token.py
index 49c8881..4f55965 100644
--- a/src/auth/token.py
+++ b/src/auth/token.py
@@ -13,11 +13,17 @@ def should_retry_rotation(error: Exception) -> bool:
-def rotate_token(client: object, token: str) -> str:
+def rotate_token(client: object, token: str, max_retries: int = 3) -> str:
+    for attempt in range(max_retries + 1):
+        try:
+            return client.rotate(token)
+        except Exception as exc:
+            if should_retry_rotation(exc) and attempt < max_retries:
+                continue
+            raise TokenRotationError("token rotation failed") from exc
"""


def result_stream(result_text: str) -> str:
    return json.dumps({"type": "result", "result": result_text}) + "\n"


def write_run(
    run_dir: Path,
    *,
    diff_text: str,
    result_text: str,
    variant: str,
    fixture_id: str = "primary-01-overlapping-file-change-v1",
) -> None:
    run_dir.mkdir(parents=True)
    (run_dir / "metrics.json").write_text(
        json.dumps(
            {
                "fixture_id": fixture_id,
                "model": "sonnet",
                "variant": variant,
                "exit_code": 0,
                "is_error": False,
                "tool_names": {"Read": 3},
            }
        ),
        encoding="utf-8",
    )
    (run_dir / "workspace.diff").write_text(diff_text, encoding="utf-8")
    (run_dir / "stream.jsonl").write_text(result_stream(result_text), encoding="utf-8")


def benchmark_result(*, risk: str = "yes", lookup: str = "yes", blocked: str = "no") -> str:
    return "\n".join(
        [
            "done",
            "",
            "AGENT_BENCHMARK_RESULT",
            f"risk_noticed: {risk}",
            f"lookup_saved: {lookup}",
            "first_useful_action: read src/auth/token.py",
            f"blocked: {blocked}",
        ]
    )


def test_parse_agent_result_block_extracts_lowercase_fields() -> None:
    parsed = parse_agent_result_block(benchmark_result(risk="YES", lookup="Unclear"))

    assert parsed["risk_noticed"] == "yes"
    assert parsed["lookup_saved"] == "unclear"
    assert parsed["blocked"] == "no"


def test_extract_final_result_text_uses_last_result_event() -> None:
    stream = "\n".join(
        [
            json.dumps({"type": "result", "result": "first"}),
            json.dumps({"type": "assistant", "message": {"content": []}}),
            json.dumps({"type": "result", "result": "second"}),
        ]
    )

    assert extract_final_result_text(stream) == "second"


def test_changed_files_and_retry_detection() -> None:
    assert changed_files_from_diff(BASELINE_DIFF) == ["src/auth/token.py"]
    assert diff_adds_retry_behavior(BASELINE_DIFF) is True


def test_quality_scores_preserved_api_above_signature_change(tmp_path: Path) -> None:
    fixture = load_fixture(FIXTURE_PATH)
    baseline_dir = tmp_path / "baseline"
    context_dir = tmp_path / "context"
    write_run(
        baseline_dir,
        diff_text=BASELINE_DIFF,
        result_text=benchmark_result(),
        variant="baseline",
    )
    write_run(
        context_dir,
        diff_text=CONTEXT_DIFF,
        result_text=benchmark_result(),
        variant="context",
    )

    baseline = assess_claude_run(fixture, baseline_dir)
    context = assess_claude_run(fixture, context_dir)

    assert baseline.preserves_existing_api == "yes"
    assert context.preserves_existing_api == "no"
    assert baseline.quality_score > context.quality_score
    assert baseline.quality_level == "review"
    assert context.quality_level == "review"
    assert "changed existing rotate_token API" in " | ".join(context.notes)


def test_quality_fails_when_source_snapshots_are_modified(tmp_path: Path) -> None:
    fixture = load_fixture(FIXTURE_PATH)
    diff = (
        BASELINE_DIFF
        + """diff --git a/source-snapshots/github/pr-482.md b/source-snapshots/github/pr-482.md
index 1111111..2222222 100644
--- a/source-snapshots/github/pr-482.md
+++ b/source-snapshots/github/pr-482.md
@@ -1 +1,2 @@
 # GitHub PR #482
+edited
"""
    )
    run_dir = tmp_path / "run"
    write_run(run_dir, diff_text=diff, result_text=benchmark_result(), variant="context")

    assessment = assess_claude_run(fixture, run_dir)

    assert assessment.quality_level == "fail"
    assert assessment.source_snapshots_touched is True


def test_quality_passes_doc_update_when_no_explicit_target_file(tmp_path: Path) -> None:
    fixture = load_fixture(
        ROOT
        / "docs/product/discovery/fixtures/benchmark/primary"
        / "primary-03-stale-process-doc-v1.json"
    )
    diff = """diff --git a/docs/release-checklist.md b/docs/release-checklist.md
index 1111111..2222222 100644
--- a/docs/release-checklist.md
+++ b/docs/release-checklist.md
@@ -1 +1,2 @@
 # Auth Service Release Checklist
+Verify the live Confluence page because the source is stale.
"""
    run_dir = tmp_path / "run"
    write_run(
        run_dir,
        diff_text=diff,
        result_text=benchmark_result(),
        variant="context",
        fixture_id="primary-03-stale-process-doc-v1",
    )

    assessment = assess_claude_run(fixture, run_dir)

    assert assessment.quality_level == "pass"
    assert assessment.quality_score == assessment.max_quality_score


def test_quality_passes_inaccessible_docs_block_without_diff(tmp_path: Path) -> None:
    fixture = load_fixture(
        ROOT
        / "docs/product/discovery/fixtures/benchmark/primary"
        / "primary-05-inaccessible-linked-docs-v1.json"
    )
    run_dir = tmp_path / "run"
    write_run(
        run_dir,
        diff_text="",
        result_text=benchmark_result(blocked="yes", lookup="unclear"),
        variant="context",
        fixture_id="primary-05-inaccessible-linked-docs-v1",
    )

    assessment = assess_claude_run(fixture, run_dir)

    assert assessment.quality_level == "pass"
    assert assessment.changed_files == []


def test_write_quality_summary_uses_lf_csv(tmp_path: Path) -> None:
    fixture = load_fixture(FIXTURE_PATH)
    run_dir = tmp_path / "run"
    write_run(run_dir, diff_text=BASELINE_DIFF, result_text=benchmark_result(), variant="baseline")
    assessment = assess_claude_run(fixture, run_dir)
    path = tmp_path / "quality.csv"

    write_quality_summary(path, [assessment])

    assert b"\r\n" not in path.read_bytes()
    with path.open(newline="", encoding="utf-8") as handle:
        rows = list(csv.DictReader(handle))
    assert rows[0]["quality_level"] == "review"
    assert rows[0]["changed_files"] == '["src/auth/token.py"]'
