# E-020 Run: First Vertical Slice V1

Date: 2026-06-15

Purpose: define the first product slice that can be prototyped before broad
connector work.

## Created Artifact

- `architecture/first-vertical-slice-v1.md`

## Decision

The first slice should be an issue-backed file edit with changed context.

It should prove the product through:

- local workspace scope,
- Git host collision signal,
- issue changed-since-start signal,
- reviewed project guidance if present,
- stale source caveat,
- terminal `Working context`,
- `Show why`,
- `Use in this session`.

## Why This Slice

It lives exactly where agents already work: in a repo, on a branch, about to edit
a file.

It can show value without asking the user to manage a memory system.

It also tests the hard trust pieces early:

- source evidence versus instruction,
- authority versus advisory context,
- freshness,
- access limitations,
- and session-only context.

## Important Recommendation

Build this with fixtures before real connectors.

The first thing to validate is the product loop, not OAuth, pagination, rate
limits, or connector edge cases.

## First Real Connector Candidate

GitHub or GitLab metadata should be the first real connector after fixtures.

File collision is more product-native than generic issue or doc retrieval. It is
scoped, explainable, and easy for an agent to act on.

## What This Says About The Product

TeamCtx is not a memory layer bolted onto agents.

It is a start/resume context layer that tells the agent what changed, what is
uncertain, and what reviewed guidance applies before work begins.

## Next Experiment

Turn this vertical slice into a prototype build plan with fixture files, command
names, and a minimal CLI flow.
