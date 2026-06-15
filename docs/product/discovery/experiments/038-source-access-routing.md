# E-038: Source Access Routing Harness

## Purpose

Separate prompt context from source availability in the Claude runtime benchmark.

## Product Question

Does TeamCtx save lookup work because it writes better prompt context, because it
routes source access, or because of both together?

## Hypothesis

Prompt gating is necessary but not sufficient. If every source snapshot is
presented as a browsable local folder, agents will often rediscover source-health
warnings even when TeamCtx does not inject a card. A useful benchmark needs a
source-access variable.

## Change

Add `--source-access` to `teamctx claude-agent-benchmark`:

- `full`: current behavior; local `source-snapshots/` are written and mentioned
  in the prompt.
- `none`: source snapshots are withheld from the workspace and the prompt says
  they are unavailable.

Future summary artifacts include a `source_access` column.

## Pass Criteria

- Existing benchmark behavior remains the default.
- `source_access=none` removes the local source snapshot directory.
- `source_access=none` removes the `source-snapshots/` prompt affordance.
- Tests pass without requiring a live Claude run.

## Next Run

Recommended first spend after this harness change:

```bash
PYTHONPATH=src python3 -m teamctx.cli claude-agent-benchmark   --fixtures-dir docs/product/discovery/fixtures/benchmark/primary   --output-dir docs/product/discovery/runs/2026-06-15-e039-source-access-none-v1   --scenario primary-03-stale-process-doc-v1   --scenario primary-04-safety-blocked-source-change-v1   --scenario primary-05-inaccessible-linked-docs-v1   --variant context   --model sonnet   --source-access none   --max-budget-usd 0.30
```

Compare that run against E-037 to isolate the cost of broad source exposure.
