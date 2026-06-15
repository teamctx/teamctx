# E-021 Run: Fixture-Backed Prototype Plan V1

Date: 2026-06-15

Purpose: make the first vertical slice buildable without starting real connector
work.

## Created Artifacts

- `architecture/prototype-build-plan-v1.md`
- `fixtures/vertical-slice/auth-token-retry-v1.json`

## Prototype Shape

The prototype should load a fixture, render `Working context`, answer `Show why`,
support `Use in this session`, and generate benchmark prompts.

Prototype commands:

```text
teamctx context --fixture fixtures/vertical-slice/auth-token-retry-v1.json
teamctx why card_pr_collision --fixture fixtures/vertical-slice/auth-token-retry-v1.json
teamctx use card_auth_notes_advisory --session demo --fixture fixtures/vertical-slice/auth-token-retry-v1.json
teamctx benchmark-prompt --scenario auth-token-retry --variant context --fixture fixtures/vertical-slice/auth-token-retry-v1.json
```

## Key Product Decision

The advisory Obsidian card is not agent-visible by default.

That is the right default for the trust model:

- it is useful to the user,
- it may become session context,
- but it is not reviewed project guidance,
- and it should not enter the agent prompt without explicit session use.

## Why This Is The Right Next Build

It tests the core product loop with no connector noise:

- scoped signals,
- authority split,
- source health,
- terminal rendering,
- explanation,
- session-only context,
- benchmark generation.

If this feels useful, real connectors have a reason to exist.

If this feels awkward, connectors will not save it.

## Next Engineering Step

Before coding, inspect the existing `teamctx` package shape and decide whether a
fixture-backed prototype can fit into the current repo without fighting it.
