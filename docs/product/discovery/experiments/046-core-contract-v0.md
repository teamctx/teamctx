# E-046: Core Contract V0

Date: 2026-06-16

## Question

Can TeamCtx define the durable objects behind terminal context before adding a
live Git-host source probe?

## Method

Implement a pure `teamctx.core.contracts` module with versioned Pydantic models,
add a golden contract fixture, and test deterministic round-trip plus unsafe
policy bypass cases.

## Result

Core Contract V0 is implemented for:

- `PolicyDecision`
- `SourceSignal`
- `SourceStatus`
- `SourceOpenTarget`
- `GuidanceRecord`
- `SessionContextUse`
- `ContextCard`
- `RequestContext`

The existing prototype remains intact, but file-backed fixture loading moved out
of `teamctx.core` into `teamctx.fixtures` so the core package stays pure.

## Product Read

This is the first real contract line between the product and future connectors.
Connectors should emit evidence, status, source-open targets, and reviewed
guidance candidates into this shape. They should not bypass it by writing
terminal cards or agent-visible source text directly.

## Decision

Proceed to the first Git-host metadata probe using Core Contract V0 as the target
normalization shape.
