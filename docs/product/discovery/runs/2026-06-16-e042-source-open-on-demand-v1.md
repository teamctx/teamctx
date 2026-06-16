# E-042 Run: Source Open On Demand V1

Date: 2026-06-16

Purpose: compare full source access with status-only plus one explicit source
open on a task where the source body carries changed acceptance criteria.

## Scope

- Model: `sonnet` (`claude-sonnet-4-6` as reported by Claude Code).
- Runs: 2 total, context variant only.
- Scenario: `primary-02-changed-acceptance-criteria-v1`.
- Source access: `full` and `status_open`.
- Per-run cap: `$0.30`.

Command shape: run `run_claude_agent(...)` for the same fixture twice, once with
`source_access="full"` and once with `source_access="status_open"`, then write
shared summary and quality artifacts under the E-042 run directory.

## Result

- Reported total cost: `$0.386376`.
- Full source cost: `$0.210772`.
- Status open cost: `$0.175604`.
- Status open delta: `-$0.035169` (`-16.7%`).
- Quality: `2 pass`, `0 review`, `0 fail`.
- Leak scan before each run: passed.

## Comparison

See `source-open-comparison.csv` and `source-open-comparison.md`.

| Metric | Full source | Status open | Status open delta |
| --- | ---: | ---: | ---: |
| Reported cost | `0.210772` | `0.175604` | `-0.035169` |
| Turns | `8` | `10` | `+2` |
| Tool calls | `7` | `9` | `+2` |
| Files read | `4` | `3` | `-1` |
| Bash commands | `2` | `4` | `+2` |

## Behavioral Read

Full source read `source-snapshots/jira/API-482.md`, then also inspected the
GitHub PR source snapshot because the source tree was available. It made a good
implementation but did not add tests.

Status open used the intended product path:

```bash
python3 .teamctx/open_source.py 'Jira API-482'
```

It opened only the Jira source body, implemented the 30-second retry window,
preserved permanent validation failures, added tests, and reported
`lookup_saved: yes`.

## Product Read

This strengthens the TeamCtx product spine:

- default context should stay compact,
- source bodies should be opened one at a time,
- the open path can preserve quality while avoiding the broad browsing behavior
  seen with full source access.

This is only a one-scenario smoke, but it is the first benchmark where the full
shape wins: status-only context plus explicit source opening was cheaper than
full source and at least as good on quality.

## Decision

Carry `status_open` forward as the main default candidate for the next benchmark
set.

Next: run this mode on a larger slice or add a purpose-built scenario where an
agent must decide between opening one source and proceeding from compact context.

## Verification

- `python3 -m compileall -q src tests`: passed.
- `python3 -m pytest`: `54 passed`.
- `python3 -m ruff check .`: all checks passed.
- `python3 -m mypy src tests`: no issues in `20` source files.
