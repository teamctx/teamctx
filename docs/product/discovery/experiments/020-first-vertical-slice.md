# E-020: First Vertical Slice

## Purpose

Define the smallest prototype that can prove TeamCtx is a product, not just a
set of docs or a memory backend.

## Product Question

What is the first slice that shows useful working context inside an agent
terminal while exercising source signals, source health, `Show why`, and session
use?

## Hypothesis

The first vertical slice should focus on one common agent task:

> edit a file for an issue-backed branch while related source state has changed.

That slice can prove the core loop without broad connectors or a dashboard.

## Required Product Behaviors

The slice must demonstrate:

- local branch/file context,
- Git host collision or recent PR/MR signal,
- issue changed-since-start signal,
- terminal `Working context` rendering,
- `Show why` explanation,
- `Use in this session`,
- and safe behavior when a source is stale, blocked, or unavailable.

## Non-Goals

- Full connector marketplace.
- Dashboard.
- Team analytics.
- Chat ingestion.
- General semantic search.
- Persistent user-facing memory.

## Output

A first vertical slice spec with user flow, backend flow, test fixtures, and
success criteria.
