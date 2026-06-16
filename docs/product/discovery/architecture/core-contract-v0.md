# Core Contract V0

Date: 2026-06-16

Status: implemented contract slice

## Purpose

Core Contract V0 is the durable shape behind the terminal context packet. It is
not the renderer and not a connector API. It is the narrow set of objects the
next Git-host probe can emit and the terminal surface can explain.

## Boundary

`teamctx.core.contracts` is pure. It validates already-parsed data and has no
filesystem, network, subprocess, randomness, or ambient-time reads. File-backed
fixture loading lives in `teamctx.fixtures`, outside the pure core package.

## Versioned Objects

V0 defines explicit schema versions for:

- `PolicyDecision`
- `SourceSignal`
- `SourceStatus`
- `SourceOpenTarget`
- `GuidanceRecord`
- `SessionContextUse`
- `ContextCard`
- `RequestContext`
- `CoreContractDocument`

Each object rejects unknown fields. The point is to keep future connector data
from smuggling behavior through unreviewed attributes.

## Product Semantics

`SourceSignal` is evidence or a caveat. It is not memory.

`SourceStatus` explains source health and safe absence. It can change confidence
without exposing source body text.

`SourceOpenTarget` is the explicit source-body escape hatch. A target can be
`available`, `status_only`, `blocked`, `unavailable`, or `not_collected`. Only
`available` targets can include source text by policy.

`GuidanceRecord` is the only active project guidance object. Active guidance
requires review metadata. Draft and retired guidance cannot render to the agent.

`SessionContextUse` records temporary session selection. It does not create
project guidance.

`ContextCard` is a view. Every V0 card carries source, reason, scope, freshness,
confidence, and source-body openability so `Show why` has enough evidence without
querying a connector.

## Fail-Closed Rules

V0 rejects:

- agent-visible policy that is not user-visible;
- source text when the source is blocked, unavailable, disabled, or status-only;
- hidden or never-visible signals that render to agents;
- active guidance without review metadata;
- draft or retired guidance that renders to agents;
- openable context cards without a source-open target;
- project-guidance cards that do not reference a guidance record;
- unknown fields on any contract object.

## Golden Fixture

The golden fixture is:

`docs/product/discovery/fixtures/contracts/v0/core-contract-document.json`

It includes a request context, GitHub collision signal, stale docs status,
source-open targets, reviewed guidance, session use, and rendered cards.

## Tests

`tests/test_core_contracts.py` proves:

- the golden fixture round-trips deterministically;
- context cards carry explainability fields;
- unknown fields cannot bypass policy;
- unsafe source-body and visibility combinations are rejected;
- active guidance requires review;
- draft guidance cannot render to the agent;
- project guidance cards reference guidance records;
- the core package avoids filesystem and runtime side-effect imports.

## Decision

Use Core Contract V0 as the target shape for the first live Git-host metadata
probe. Do not add live connector fields directly to rendered cards or benchmark
fixtures unless they first fit one of these V0 objects.
