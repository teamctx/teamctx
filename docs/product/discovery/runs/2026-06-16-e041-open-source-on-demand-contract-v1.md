# E-041 Run: Source Open On Demand Contract V1

Date: 2026-06-16

Purpose: prove the explicit source-body path after E-040 status-only routing.

## Scope

This was a local fixture-backed implementation experiment, not an external model
benchmark.

Implemented:

- optional `source_artifacts` on fixtures,
- `render_open_source(fixture, ref_id)`,
- `teamctx open-source <card-or-source-id> --fixture ...`,
- a vertical-slice GitHub PR body that can be opened only by explicit action,
- tests for allowed, stale/denied, unknown, and blocked-body cases.

## CLI Smoke

Allowed source body:

```bash
PYTHONPATH=src python3 -m teamctx.cli open-source card_pr_collision \
  --fixture docs/product/discovery/fixtures/vertical-slice/auth-token-retry-v1.json
```

Output shape:

```text
Open source

GitHub PR #482
Freshness: fresh

GitHub PR #482

Summary: add retry handling for token rotation when the upstream client times out.
Files touched: src/auth/token.py.
Review note: keep legacy client behavior unchanged.
```

Stale source without source-body permission:

```text
Open source

Confluence Release Checklist
Freshness: stale
Use as background only. Verify before relying.

Source body unavailable.
Reason: TeamCtx can show the status, but not the source body.
```

## Result

The contract works as a product boundary:

- source bodies stay out of default context and benchmark prompts,
- opening is per-source, not a workspace folder,
- stale source state remains visible as a caveat,
- blocked and unavailable sources do not leak body text.

## Decision

Keep status-only source routing as the default. Add open-on-demand as an explicit
secondary path for cases where one source body is actually needed.

The next benchmark should test an agent task where compact status is not enough
and a single allowed source body is useful. The measurement should ask whether
opening one source saves lookup work without recreating the full-source browsing
cost from E-037.

## Verification

- `python3 -m compileall -q src tests`: passed.
- `python3 -m pytest`: `51 passed`.
- `python3 -m ruff check .`: all checks passed.
- `python3 -m mypy src tests`: no issues in `20` source files.
- `git diff --check`: passed.
