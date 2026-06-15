# E-023 Run: Implementation Spike Plan V1

Date: 2026-06-15

Purpose: make the first code spike precise while keeping the work in discovery
mode.

## Created Artifact

- `architecture/prototype-implementation-spike-v1.md`

## Decision

If we code next, build a fixture-backed prototype inside the existing package:

```text
src/teamctx/core/
```

Do not create a physical `teamctx-core` package yet.

## What The Spike Proves

- The source-signal contract can produce a terminal `Working context` block.
- Advisory note context can stay out of the default agent prompt.
- `Show why` can explain cards without leaking source bodies.
- `Use in this session` can be temporary and non-guidance.
- E-014 benchmark prompts can be generated from the same fixture.

## What The Spike Refuses

- No live connectors.
- No dashboard.
- No cloud storage.
- No broad search.
- No memory/ledger/registry language.

## CTO Read

This is the right build only if we want to test product feel in a terminal. It is
not yet the right build if we still want more naming/product strategy first.
