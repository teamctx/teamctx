# E-040 Run: Source Status Only V1

Date: 2026-06-15

Purpose: test compact source status as the default alternative to broad source
snapshots and total source absence.

## Scope

- Model: `sonnet` (`claude-sonnet-4-6` as reported by Claude Code).
- Runs: 3 total, context variant only.
- Scenarios: primary 03, 04, and 05.
- Source access: `status_only`.
- Per-run cap: `$0.30`.

Command:

```bash
PYTHONPATH=src python3 -m teamctx.cli claude-agent-benchmark \
  --fixtures-dir docs/product/discovery/fixtures/benchmark/primary \
  --output-dir docs/product/discovery/runs/2026-06-15-e040-source-status-only-v1 \
  --scenario primary-03-stale-process-doc-v1 \
  --scenario primary-04-safety-blocked-source-change-v1 \
  --scenario primary-05-inaccessible-linked-docs-v1 \
  --variant context \
  --model sonnet \
  --source-access status_only \
  --max-budget-usd 0.30
```

## Result

- Reported cost: `$0.282821`.
- Quality: `3 pass`, `0 review`, `0 fail`.
- Leak scan before each run: passed.

## Comparison

See `source-routing-comparison.csv` and `source-routing-comparison.md`.

Aggregate for the three warning scenarios:

| Metric | E-035 baseline | E-037 gated/full source | E-039 gated/no source | E-040 gated/status-only | Status-only vs baseline | Status-only vs full source | Status-only vs no source |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| Reported cost | `0.354957` | `0.447406` | `0.287766` | `0.282821` | `-0.072136` | `-0.164585` | `-0.004944` |
| Turns | `28` | `30` | `22` | `21` | `-7` | `-9` | `-1` |
| Tool calls | `25` | `27` | `19` | `18` | `-7` | `-9` | `-1` |
| Files read | `20` | `21` | `14` | `9` | `-11` | `-12` | `-5` |

## Product Read

Status-only source routing is now the best default candidate. It keeps the
source-health facts that change agent confidence, but does not hand the agent a
browsable `source-snapshots/` tree.

This fixed the key E-039 flaw. In scenario 3, the agent updated the release
checklist from local files but explicitly marked the Confluence source as stale
and called for a final cross-check before signoff. In scenario 4, it stopped
instead of guessing at a safety-filtered Jira change. In scenario 5, it stopped
because the linked docs were inaccessible.

The product shape should be:

- compact source status is available by default when it changes confidence,
- source bodies are opened only on explicit user/agent action or policy need,
- stale/unavailable/blocked status is treated as a confidence boundary, not as
  task instructions.

## Decision

Use status-only source routing as the next default candidate for the TeamCtx
agent-terminal surface.

The next hard part is designing the open-on-demand path: how the user or agent
asks for a source body, what policy allows it, and how the product avoids
turning that into another pile of files to browse.

## Verification

- `python3 -m pytest`: `45 passed`.
- `python3 -m ruff check .`: all checks passed.
- `python3 -m mypy src tests`: no issues in `18` source files.
- `git diff --check`: passed.
