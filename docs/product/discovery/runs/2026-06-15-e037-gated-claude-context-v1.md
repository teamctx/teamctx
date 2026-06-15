# E-037 Run: Gated Claude Context V1

Date: 2026-06-15

Purpose: run a targeted Claude Code benchmark after E-036 prompt gating.

## Scope

- Model: `sonnet` (`claude-sonnet-4-6` as reported by Claude Code).
- Runs: 3 total, context variant only.
- Scenarios: primary 03, 04, and 05.
- Per-run cap: `$0.30`.

Command:

```bash
PYTHONPATH=src python3 -m teamctx.cli claude-agent-benchmark   --fixtures-dir docs/product/discovery/fixtures/benchmark/primary   --output-dir docs/product/discovery/runs/2026-06-15-e037-gated-claude-context-v1   --scenario primary-03-stale-process-doc-v1   --scenario primary-04-safety-blocked-source-change-v1   --scenario primary-05-inaccessible-linked-docs-v1   --variant context   --model sonnet   --max-budget-usd 0.30
```

## Result

- Reported cost: `$0.447406`.
- Quality: `3 pass`, `0 review`, `0 fail`.
- Leak scan before each run: passed.

## Comparison With E-035

See `gated-comparison.csv` and `gated-comparison.md`.

Aggregate for the three changed scenarios:

| Metric | E-035 baseline | E-035 old context | E-037 gated context | Gated vs baseline | Gated vs old context |
| --- | ---: | ---: | ---: | ---: | ---: |
| Reported cost | `0.354957` | `0.494141` | `0.447406` | `0.092449` | `-0.046735` |
| Turns | `28` | `36` | `30` | `2` | `-6` |
| Tool calls | `25` | `33` | `27` | `2` | `-6` |
| Files read | `20` | `24` | `21` | `1` | `-3` |

## Product Read

Prompt gating helped. It reduced the old warning-context overhead on the changed
scenario set, especially the blocked-source scenario.

But prompt gating did not beat baseline overall. The benchmark still exposes a
broad `source-snapshots/` directory to every variant and tells the agent those
snapshots may be useful. Even when TeamCtx injects no default card, the agent can
rediscover stale, blocked, or inaccessible-source evidence by browsing local
snapshots.

This means the token-savings claim depends on source access routing, not just
prompt gating. TeamCtx needs to decide what to place directly in the agent
prompt, what to keep inspectable, and when source details should become
available. A plain folder of source snapshots is too tempting and too broad if
we are trying to reduce lookup work.

## Decision

Keep E-036 prompt gating. Add the next product experiment around source access
routing:

- direct task-changing context in the prompt,
- source-health context available through inspection,
- source snapshots opened only on demand or through a narrower source-status
  surface,
- benchmark variants that distinguish prompt context from source availability.
