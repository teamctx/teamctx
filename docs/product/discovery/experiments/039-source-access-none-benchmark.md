# E-039: Source Access None Benchmark

## Purpose

Run the E-037 warning scenarios again with source snapshots withheld.

## Product Question

Is broad source availability the remaining cost driver after agent prompt gating?

## Hypothesis

Withholding source snapshots should reduce lookup work compared with E-037 full
source access. Quality may reveal where missing source state creates safety or
confidence loss.

## Scope

Run context variants for:

- `primary-03-stale-process-doc-v1`
- `primary-04-safety-blocked-source-change-v1`
- `primary-05-inaccessible-linked-docs-v1`

Settings:

- Model: `sonnet`.
- Source access: `none`.
- Per-run cap: `$0.30`.

## Pass Criteria

- Quality remains pass-level.
- Aggregate cost, turns, tool calls, and reads decrease versus E-037 full source
  access.
- Result clarifies whether source availability needs a middle mode.

## Output

- `runs/2026-06-15-e039-source-access-none-v1/summary.csv`
- `runs/2026-06-15-e039-source-access-none-v1/quality.csv`
- `runs/2026-06-15-e039-source-access-none-v1/source-access-comparison.csv`
