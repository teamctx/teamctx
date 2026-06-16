# E-042: Source Open On Demand Benchmark

## Purpose

Test whether status-only context plus one explicit source open can beat full
source access on a task where the source body contains useful acceptance detail.

## Product Question

Can TeamCtx save lookup cost without losing quality by exposing one requested
source body instead of a browsable `source-snapshots/` tree?

## Hypothesis

`status_open` should preserve pass-level quality while reducing source browsing
and reported cost compared with full source access.

## Scope

Run `primary-02-changed-acceptance-criteria-v1` twice:

- context variant with full source snapshots,
- context variant with `status_open`.

Settings:

- Model: `sonnet`.
- Per-run cap: `$0.30`.
- Source body under test: `Jira API-482`.

## Pass Criteria

- Both variants pass quality scoring.
- `status_open` uses `.teamctx/open_source.py` to open `Jira API-482`.
- `status_open` does not expose or read a `source-snapshots/` directory.
- `status_open` is no worse than full source on task quality.
- Result clarifies cost/tool tradeoff versus full source browsing.

## Output

- `runs/2026-06-16-e042-source-open-on-demand-v1/summary.csv`
- `runs/2026-06-16-e042-source-open-on-demand-v1/quality.csv`
- `runs/2026-06-16-e042-source-open-on-demand-v1/source-open-comparison.csv`
