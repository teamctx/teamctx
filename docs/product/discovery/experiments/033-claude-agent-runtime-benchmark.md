# E-033: Claude Agent Runtime Benchmark

## Purpose

Move from chat-prompt benchmarking to actual Claude Code agent-runtime
measurement in disposable repositories.

## Product Question

Does TeamCtx working context reduce cold-start lookup work, token cost, and
time-to-useful-action when the agent has tools?

## Hypothesis

When a task-relevant context card is supplied at the start of an agent run,
Claude Code should need fewer turns, fewer tool calls, fewer file reads, and
less total reported cost to reach a useful action.

## Method

- Seed a disposable repo for each benchmark fixture.
- Provide local source snapshots as stand-ins for GitHub, Jira, and docs lookups.
- Run Claude Code once without TeamCtx context and once with TeamCtx context.
- Capture stream JSON, cost, token usage, tool calls, file reads, final answer,
  and workspace diff.

## Output

- `teamctx claude-agent-benchmark` command.
- `src/teamctx/claude_benchmark.py` harness.
- `runs/2026-06-15-e033-claude-agent-runtime-v1/` first Sonnet run.
