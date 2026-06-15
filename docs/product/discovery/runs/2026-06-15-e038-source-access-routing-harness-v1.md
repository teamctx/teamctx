# E-038 Run: Source Access Routing Harness V1

Date: 2026-06-15

Purpose: make the Claude runtime benchmark capable of testing source availability
separately from TeamCtx prompt context.

## Change

The Claude benchmark harness now supports `source_access`:

- `full`: default, preserves existing runs. The workspace includes
  `source-snapshots/`, and the prompt tells the agent it may inspect them.
- `none`: the workspace does not include `source-snapshots/`, and the prompt says
  local source snapshots are unavailable.

New runs record `source_access` in `summary.csv` and `summary.md`. Non-default
run directories append `-source-none` so they do not collide with default runs.

## Why This Matters

E-037 showed that prompt gating reduced overhead compared with old warning
context, but did not beat baseline while broad local source snapshots remained
available. The agent could still browse snapshots and rediscover source-health
warnings.

This harness change lets the next experiment isolate the product question:

- prompt context only,
- source access only,
- prompt context plus source access.

## Verification

Focused checks:

- `python3 -m pytest tests/test_claude_benchmark.py`: `11 passed`.
- CLI smoke: `PYTHONPATH=src python3 -m teamctx.cli claude-agent-benchmark --help`.
- Prompt smoke: `render_agent_prompt(..., source_access="none")` removes the
  `source-snapshots/` affordance.

Full verification:

- `python3 -m compileall -q src tests`
- `python3 -m pytest`: `42 passed`
- `python3 -m ruff check .`: all checks passed
- `python3 -m mypy src tests`: no issues in `18` source files
