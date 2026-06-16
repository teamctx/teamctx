# E-044: Source Openability Smoke

## Purpose

Test whether explicitly labeling source-body availability improves `status_open` behavior without breaking the body-available path.

## Product Question

If the prompt tells the agent which sources can return body text, will it avoid unsafe or wasteful source-opening behavior?

## Scope

Run two primary scenarios with `status_open`:

- `primary-01-overlapping-file-change-v1`: source body unavailable for a same-file PR collision.
- `primary-02-changed-acceptance-criteria-v1`: source body available for Jira acceptance criteria.

Settings:

- Model: `sonnet`.
- Variant: `context`.
- Per-run cap: `$0.30`.

## Pass Criteria

- Collision scenario preserves the existing API or blocks/reviews instead of rewriting it.
- Jira scenario still opens `Jira API-482` and passes quality scoring.
- No source bodies are exposed through a browsable source snapshot tree.

## Output

- `runs/2026-06-16-e044-source-openability-smoke-v1/summary.csv`
- `runs/2026-06-16-e044-source-openability-smoke-v1/quality.csv`
- `runs/2026-06-16-e044-source-openability-smoke-v1/source-openability-comparison.csv`
