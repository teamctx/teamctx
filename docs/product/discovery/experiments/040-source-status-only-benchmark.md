# E-040: Source Status Only Benchmark

## Purpose

Test the middle source-routing mode predicted by E-039: no broad source
snapshots, but compact stale/unavailable/blocked source status in the agent
prompt.

## Product Question

Can TeamCtx preserve useful source-health warnings without inviting agents to
browse source bodies?

## Hypothesis

Status-only source routing should keep quality at pass level, reduce lookup work
versus E-037 full source access, and avoid the E-039 failure mode where a stale
local export looked silently safe.

## Scope

Run context variants for:

- `primary-03-stale-process-doc-v1`
- `primary-04-safety-blocked-source-change-v1`
- `primary-05-inaccessible-linked-docs-v1`

Settings:

- Model: `sonnet`.
- Source access: `status_only`.
- Per-run cap: `$0.30`.

## Pass Criteria

- Quality remains pass-level.
- Aggregate cost, turns, tool calls, and reads decrease versus E-037 full source
  access.
- Scenario 3 notices stale Confluence status before updating the local release
  checklist.
- Scenarios 4 and 5 block or pause when the source status says the needed
  evidence is blocked or unavailable.

## Output

- `runs/2026-06-15-e040-source-status-only-v1/summary.csv`
- `runs/2026-06-15-e040-source-status-only-v1/quality.csv`
- `runs/2026-06-15-e040-source-status-only-v1/source-routing-comparison.csv`
