from __future__ import annotations

import csv
import json
from pathlib import Path

from teamctx.claude_benchmark import (
    AgentVariant,
    SourceAccessMode,
    benchmark_fixture_paths,
    claude_command,
    parse_claude_stream,
    prepare_agent_workspace,
    render_agent_prompt,
    sanitize_claude_stream,
    write_summary,
)
from teamctx.core.fixtures import load_fixture

ROOT = Path(__file__).resolve().parent.parent
BENCHMARK_FIXTURES = ROOT / "docs/product/discovery/fixtures/benchmark/primary"


def first_fixture_path() -> Path:
    return BENCHMARK_FIXTURES / "primary-01-overlapping-file-change-v1.json"


def test_render_agent_prompt_adds_working_context_only_for_context_variant() -> None:
    fixture = load_fixture(first_fixture_path())

    baseline = render_agent_prompt(fixture, "baseline")
    context = render_agent_prompt(fixture, "context")

    assert "No TeamCtx working context" in baseline
    assert "Working context" not in baseline
    assert "Local source snapshots may be under source-snapshots/" in context
    assert "Working context" in context
    assert "Another open PR changed src/auth/token.py 11 minutes ago." in context
    assert "AGENT_BENCHMARK_RESULT" in context


def test_render_agent_prompt_can_withhold_source_snapshots() -> None:
    fixture = load_fixture(first_fixture_path())

    prompt = render_agent_prompt(fixture, "context", source_access="none")

    assert "Complete the task if you can do so safely from local files." in prompt
    assert "No local source snapshots are available in this run." in prompt
    assert "source-snapshots/" not in prompt
    assert "Another open PR changed src/auth/token.py 11 minutes ago." in prompt


def test_prepare_agent_workspace_creates_code_and_source_snapshots(tmp_path: Path) -> None:
    fixture = load_fixture(first_fixture_path())
    workspace = tmp_path / "workspace"

    prepare_agent_workspace(fixture, workspace)

    assert (workspace / "src/auth/token.py").exists()
    assert (workspace / "tests/test_token_rotation.py").exists()
    assert (workspace / "source-snapshots/github/pr-482.md").exists()
    assert "src/auth/token.py" in (workspace / "source-snapshots/github/pr-482.md").read_text(
        encoding="utf-8"
    )
    assert (workspace / ".git").exists()


def test_prepare_agent_workspace_can_withhold_source_snapshots(tmp_path: Path) -> None:
    fixture = load_fixture(first_fixture_path())
    workspace = tmp_path / "workspace"

    prepare_agent_workspace(fixture, workspace, source_access="none")

    assert (workspace / "src/auth/token.py").exists()
    assert not (workspace / "source-snapshots").exists()
    assert "withheld" in (workspace / "README.md").read_text(encoding="utf-8")
    assert (workspace / ".git").exists()


def test_sanitize_claude_stream_drops_system_environment_events() -> None:
    raw = "\n".join(
        [
            json.dumps(
                {
                    "type": "system",
                    "subtype": "init",
                    "memory_paths": {"auto": "/home/user/.claude/memory"},
                }
            ),
            json.dumps({"type": "assistant", "message": {"content": []}}),
            json.dumps({"type": "result", "total_cost_usd": 0.01}),
        ]
    )

    sanitized = sanitize_claude_stream(raw)

    assert "memory_paths" not in sanitized
    assert '"type": "system"' not in sanitized
    assert '"type": "assistant"' in sanitized
    assert '"type": "result"' in sanitized


def test_parse_claude_stream_counts_tools_and_cost() -> None:
    lines = [
        json.dumps(
            {
                "type": "assistant",
                "message": {
                    "content": [
                        {
                            "type": "tool_use",
                            "name": "Read",
                            "input": {"file_path": "src/auth/token.py"},
                        },
                        {"type": "tool_use", "name": "Bash", "input": {"command": "pytest"}},
                    ]
                },
            }
        ),
        json.dumps(
            {
                "type": "result",
                "is_error": False,
                "duration_ms": 1234,
                "num_turns": 2,
                "total_cost_usd": 0.12,
                "usage": {
                    "input_tokens": 10,
                    "cache_creation_input_tokens": 20,
                    "cache_read_input_tokens": 30,
                    "output_tokens": 40,
                },
                "permission_denials": [],
                "result": "done",
            }
        ),
    ]

    metrics = parse_claude_stream(
        lines,
        fixture_id="fixture",
        model="sonnet",
        variant="context",
        run_dir="run",
        exit_code=0,
    )

    assert metrics.tool_calls == 2
    assert metrics.files_read == 1
    assert metrics.bash_commands == 1
    assert metrics.total_cost_usd == 0.12
    assert metrics.output_tokens == 40
    assert metrics.source_access == "full"
    assert metrics.tool_names == {"Bash": 1, "Read": 1}


def test_write_summary_uses_lf_csv(tmp_path: Path) -> None:
    metrics = parse_claude_stream(
        [
            json.dumps(
                {
                    "type": "result",
                    "is_error": False,
                    "duration_ms": 1,
                    "num_turns": 1,
                    "total_cost_usd": 0.01,
                    "usage": {},
                    "permission_denials": [],
                    "result": "done",
                }
            )
        ],
        fixture_id="fixture",
        model="sonnet",
        variant="baseline",
        run_dir="run",
        exit_code=0,
    )
    path = tmp_path / "summary.csv"

    write_summary(path, [metrics])

    raw = path.read_bytes()
    assert b"\r\n" not in raw
    with path.open(newline="", encoding="utf-8") as handle:
        rows = list(csv.DictReader(handle))
    assert rows[0]["fixture_id"] == "fixture"
    assert rows[0]["source_access"] == "full"
    assert rows[0]["tool_names"] == "{}"


def test_claude_command_terminates_variadic_allowed_tools_before_prompt() -> None:
    command = claude_command(model="sonnet", max_budget_usd=0.25, prompt="hello")

    assert "--disable-slash-commands" in command
    assert "--allowedTools" in command
    assert command[-2:] == ["--", "hello"]


def test_benchmark_fixture_paths_returns_primary_fixtures() -> None:
    paths = benchmark_fixture_paths(BENCHMARK_FIXTURES)

    assert len(paths) == 6
    assert all(path.name.startswith("primary-") for path in paths)


def test_agent_variant_type_is_limited() -> None:
    variant: AgentVariant = "baseline"

    assert variant == "baseline"


def test_source_access_mode_type_is_limited() -> None:
    mode: SourceAccessMode = "none"

    assert mode == "none"
