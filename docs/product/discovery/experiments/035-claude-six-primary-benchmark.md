# E-035: Claude Six Primary Benchmark

## Purpose

Run all six primary benchmark scenarios through the Claude Code runtime
harness with quality scoring enabled.

## Product Question

Does TeamCtx working context reduce agent lookup work and cost across the
primary scenario set while preserving quality?

## Hypothesis

Working context should reduce lookup work most when it points to a specific
fresh task-changing signal. It may add cost when it functions as caution or
source-health warning rather than direct action context.

## Output

- `runs/2026-06-15-e035-claude-six-primary-v1/summary.csv`
- `runs/2026-06-15-e035-claude-six-primary-v1/quality.csv`
- `runs/2026-06-15-e035-claude-six-primary-v1/deltas.csv`
