# E-027 Run: Fixture Prototype Implementation V1

Date: 2026-06-15

Purpose: record the first executable TeamCtx working-context prototype.

## Implemented Files

- `src/teamctx/core/models.py`
- `src/teamctx/core/fixtures.py`
- `src/teamctx/core/cards.py`
- `src/teamctx/context.py`
- `src/teamctx/render.py`
- `src/teamctx/why.py`
- `src/teamctx/session.py`
- `src/teamctx/cli.py`
- `tests/test_fixture_prototype.py`

## Implemented Commands

```text
teamctx context --fixture docs/product/discovery/fixtures/vertical-slice/auth-token-retry-v1.json
teamctx why card_pr_collision --fixture docs/product/discovery/fixtures/vertical-slice/auth-token-retry-v1.json
teamctx use card_auth_notes_advisory --session demo --fixture docs/product/discovery/fixtures/vertical-slice/auth-token-retry-v1.json
teamctx benchmark-prompt --scenario auth-token-retry --variant context --fixture docs/product/discovery/fixtures/vertical-slice/auth-token-retry-v1.json
```

For local source-layout smoke tests:

```text
PYTHONPATH=src python3 -m teamctx.cli context --fixture docs/product/discovery/fixtures/vertical-slice/auth-token-retry-v1.json
```

## Prototype Behavior

Default working context renders:

- Git host file collision.
- Issue changed since branch start.
- Reviewed project guidance.

It does not render by default:

- advisory Obsidian note match,
- stale release checklist caveat for a non-release task.

After explicit session use, the advisory note appears under `Good to know`, not
`Project guidance`.

## Verification

Passed:

```text
python3 -m compileall src/teamctx tests/test_fixture_prototype.py
python3 -m pytest tests/test_fixture_prototype.py
python3 -m pytest
python3 -m ruff check .
python3 -m mypy src tests
```

Final observed results:

- `pytest`: 11 passed.
- `ruff`: all checks passed.
- `mypy`: no issues in 12 source files.

CLI smoke tests passed for:

- `context`,
- `why`,
- `benchmark-prompt`,
- `use` plus session-aware `context`.

## Product Findings

The executable prototype supports the current product thesis.

The terminal surface feels closer to `git status, but for team context` than to a
memory product.

The most important behavior is the trust boundary:

- default context is compact and scoped,
- advisory note context requires explicit session use,
- source-health caveats need relevance gates,
- reviewed guidance is separate from advisory context.

## Engineering Findings

Keeping the first durable-core boundary inside `src/teamctx/core/` was the right
move. A separate physical `teamctx-core` package would have added packaging
complexity without improving the prototype.

The existing ADRs still fit if interpreted as:

- artifacts normalize provider data,
- relationships connect artifacts to task scope,
- source signals produce cards,
- cards render working context.

## Next Product Question

Now that the fixture loop works, the next useful evidence is probably a model
benchmark using E-014 prompts generated or mirrored from the fixture.

A real connector can wait until the benchmark shows that the context improves
agent behavior.
