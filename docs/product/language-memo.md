# Product Language Memo

Date: 2026-06-16

## Decision

Use plain terminal language. Do not require users to learn internal terms like
source signal, promotion, durable core, registry, ledger, authority tier, or
source routing.

## Current Product Words

- `Working context`: the short terminal block shown before or during agent work.
- `Show why`: explains why a card appeared, what source it came from, freshness,
  scope, confidence, and whether source text was shown.
- `Open source`: inspects the original source only when policy allows it. For
  status-only sources, it explains that source body text is unavailable.
- `Source status`: a warning or caveat when a configured source is stale,
  unavailable, blocked, or incomplete.
- `Use in this session`: temporary context for the current agent session only.

## Words To Avoid In User-Facing Surfaces

- memory
- ledger
- registry
- promotion
- quarantine
- source signal
- advisory match
- authority tier
- normalized artifact
- durable core

## Product Promise

`teamctx` should feel like `git status` for team context. It should tell the user
what changed the risk of the current work, where that fact came from, and what
was unavailable. It should not sound like surveillance, memory, or enterprise
search.

## Current Command Language

```bash
teamctx refresh
teamctx context
teamctx why <card-id>
teamctx open-source <card-or-source-id>
```

`refresh` is the only slightly technical word here, but it matches developer
expectations and has a concrete effect: update the local context file from
configured source metadata.

## Open Product Question

`open-source` may become source-family-specific later: `open-pr`, `open-issue`,
or `open-doc`. For Sprint 01, keep one command because source bodies are still
gated and mostly status-only.
