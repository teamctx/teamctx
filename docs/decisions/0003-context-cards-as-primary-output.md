# ADR 0003: Context Cards As Primary Output

- Status: accepted
- Date: 2026-06-14

## Context

Broad context dumps are noisy and unsafe. Durable memory systems solve a
different problem than just-in-time artifact awareness.

## Decision

The primary output of `teamctx` is a small set of context cards.

Cards are broker-authored facts with source links, reasons, timestamps, severity,
and omission metadata. They are not arbitrary source bodies or model-generated
summaries.

## Consequences

- The API stays compact.
- Every returned item is explainable.
- Large source bodies stay out of the main channel.
- Connectors and policy can evolve without changing the product's central UX.

