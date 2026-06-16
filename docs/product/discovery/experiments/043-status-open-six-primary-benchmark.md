# E-043: Status Open Six Primary Benchmark

## Purpose

Test whether `status_open` holds up across the full six primary Claude Code scenarios after the one-scenario E-042 smoke.

## Product Question

Can TeamCtx replace broad source snapshots with compact status plus explicit source opening without losing quality or spending more than full source access?

## Hypothesis

`status_open` should beat full source access on aggregate cost and preserve pass-level quality, but it may cost more than plain status-only on source-health warning scenarios where no source body is available.

## Scope

Run all six primary fixtures with:

- Model: `sonnet`.
- Variant: `context`.
- Source access: `status_open`.
- Per-run cap: `$0.30`.

Compare against:

- E-035 context/full-source six-primary run.
- E-040 status-only warning-scenario run for scenarios 3-5.

## Pass Criteria

- No scenario fails deterministic quality scoring.
- Source bodies are not exposed through `source-snapshots/`.
- The benchmark workspace does not contain a browsable source payload file.
- The run clarifies whether `status_open` is a default, a capability, or a narrower escape hatch.

## Output

- `runs/2026-06-16-e043-status-open-six-primary-v1/summary.csv`
- `runs/2026-06-16-e043-status-open-six-primary-v1/quality.csv`
- `runs/2026-06-16-e043-status-open-six-primary-v1/status-open-six-primary-comparison.csv`
- `runs/2026-06-16-e043-status-open-six-primary-v1/status-open-warning-comparison.csv`
