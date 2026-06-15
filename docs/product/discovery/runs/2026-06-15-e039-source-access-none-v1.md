# E-039 Run: Source Access None V1

Date: 2026-06-15

Purpose: test whether broad source snapshot exposure is the remaining cost driver
after E-036 prompt gating.

## Scope

- Model: `sonnet` (`claude-sonnet-4-6` as reported by Claude Code).
- Runs: 3 total, context variant only.
- Scenarios: primary 03, 04, and 05.
- Source access: `none`.
- Per-run cap: `$0.30`.

Command:

```bash
PYTHONPATH=src python3 -m teamctx.cli claude-agent-benchmark   --fixtures-dir docs/product/discovery/fixtures/benchmark/primary   --output-dir docs/product/discovery/runs/2026-06-15-e039-source-access-none-v1   --scenario primary-03-stale-process-doc-v1   --scenario primary-04-safety-blocked-source-change-v1   --scenario primary-05-inaccessible-linked-docs-v1   --variant context   --model sonnet   --source-access none   --max-budget-usd 0.30
```

## Result

- Reported cost: `$0.287766`.
- Quality: `3 pass`, `0 review`, `0 fail`.
- Leak scan before each run: passed.

## Comparison

See `source-access-comparison.csv` and `source-access-comparison.md`.

Aggregate for the three warning scenarios:

| Metric | E-035 baseline | E-037 gated/full source | E-039 gated/no source | No source vs baseline | No source vs full source |
| --- | ---: | ---: | ---: | ---: | ---: |
| Reported cost | `0.354957` | `0.447406` | `0.287766` | `-0.067191` | `-0.159641` |
| Turns | `28` | `30` | `22` | `-6` | `-8` |
| Tool calls | `25` | `27` | `19` | `-6` | `-8` |
| Files read | `20` | `21` | `14` | `-6` | `-7` |

## Product Read

This is the strongest cost-saving signal so far. Broad source exposure is a real
cost driver. When local source snapshots were withheld, the same warning scenario
set became cheaper than both E-037 gated/full-source context and E-035 baseline.

But `none` is not the final product shape. Scenario 3 updated the local release
checklist from a stale export without knowing the upstream source-health caveat.
Scenarios 4 and 5 blocked quickly because the linked issue/docs were unavailable,
which was safe and cheap but still a blunt behavior.

The product needs a middle mode: compact source status without broad source body
exposure. Agents should know when source health changes confidence, but should
not be invited to browse every available source snapshot by default.

## Decision

Next experiment should test `status-only` source routing:

- no broad `source-snapshots/` directory,
- compact stale/unavailable/blocked status in prompt or side-channel,
- no source body unless explicitly opened,
- compare against E-037 full-source and E-039 no-source runs.

## Verification

- `python3 -m pytest`: `42 passed`.
- `python3 -m ruff check .`: all checks passed.
- `python3 -m mypy src tests`: no issues in `18` source files.
- `git diff --check`: passed.
