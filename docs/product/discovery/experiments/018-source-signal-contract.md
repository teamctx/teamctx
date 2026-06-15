# E-018: Source Signal Contract

## Purpose

Turn the source-signal fixtures into a first data and rendering contract.

The product needs a backend shape that supports working context without becoming
memory, a ledger, a registry, or a general search index.

## Product Question

What is the smallest durable object that can produce trustworthy working context
for an agent terminal?

## Hypothesis

The durable object should be a scoped source signal, not a memory entry.

A source signal says:

- what changed or matters,
- where the evidence came from,
- what scope it applies to,
- whether it is fresh, stale, blocked, or unavailable,
- whether it can be shown to the agent,
- and how the renderer should frame it.

## Contract Requirements

The contract must support:

- working context cards,
- `Show why`,
- safe degradation when sources fail,
- advisory matches versus reviewed guidance,
- session-only use,
- future guidance drafts,
- source omission rules,
- and benchmarkable agent behavior.

## Non-Goals

- Storing all user work.
- Tracking all activity.
- Recreating every source document.
- Letting source text become instruction text.
- Making users manage internal terms.

## Output

A V1 source-signal contract and rendering rules.
