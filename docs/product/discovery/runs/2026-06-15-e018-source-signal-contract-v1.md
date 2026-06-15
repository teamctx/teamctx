# E-018 Run: Source Signal Contract V1

Date: 2026-06-15

Purpose: convert fixtures and authority-language decisions into a first backend
contract.

## Created Artifact

- `architecture/source-signal-contract-v1.md`

## Main Decision

The backend starts with `SourceSignal`, `GuidanceRecord`, `SessionContextUse`, and
`SourceStatus`.

It does not start with a generic memory record.

## Why This Matters

A memory-shaped object pulls the product toward storage, retrieval, and broad
recall.

A signal-shaped object pulls the product toward scoped, explainable working
context.

That fits the actual problem better: the agent needs to know what changes the
next action, not everything the team has ever done.

## Important Design Move

The rendered card is a view over source signals and guidance records.

This keeps product language flexible while preserving a stricter internal model:

- source signal: evidence or caveat,
- guidance record: reviewed scoped guidance,
- session use: temporary agent-visible selection,
- source status: health and safe absence.

## Risk Found

`approved_guidance` may not belong as a `signal_type` at all.

It may be cleaner to make approved guidance only a `GuidanceRecord`, while source
signals can suggest `Draft guidance`. That would prevent source normalization from
accidentally creating authority.

## Recommendation

Keep `approved_guidance` in the discovery contract for benchmark continuity, but
try to remove it from the implementation data model unless a strong reason
appears.

The implementation model would become:

- `SourceSignal`: evidence, caveats, advisory matches, collisions, runtime state.
- `GuidanceRecord`: reviewed project guidance.

## Next Question

What package owns this contract?

This leads directly to the TeamCtx plus durable-core package boundary.
