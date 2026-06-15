# E-037: Gated Context Rerun

## Purpose

Validate the E-036 agent prompt gate with a targeted Claude rerun.

## Product Question

Does removing stale, blocked, and unavailable source-health cards from default
agent prompts reduce the warning-context overhead seen in E-035?

## Hypothesis

For the three changed scenarios, gated context should cost less than the old
context prompts while preserving quality. It may not beat baseline because the
benchmark still exposes local source snapshots to every variant.

## Scope

Run only context variants for the scenarios whose prompt cards changed:

- `primary-03-stale-process-doc-v1`
- `primary-04-safety-blocked-source-change-v1`
- `primary-05-inaccessible-linked-docs-v1`

Compare against E-035 baseline and old context results.

## Pass Criteria

- Gated context quality remains pass-level.
- Gated context reduces aggregate turns/tools/reads versus old context.
- The result clarifies whether prompt gating alone is enough for the token claim.

## Output

- `runs/2026-06-15-e037-gated-claude-context-v1/summary.csv`
- `runs/2026-06-15-e037-gated-claude-context-v1/quality.csv`
- `runs/2026-06-15-e037-gated-claude-context-v1/gated-comparison.csv`
