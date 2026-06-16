# Build Plan

This file is the live sequencing overview for TeamCtx. The detailed engineering
backlog remains in [Implementation Plan](implementation-plan.md), but this file
tracks the current product-building order after the Ambara pivot and Sprint 01.

## Built

Sprint 01 proved the first narrow product spine:

- fixture-backed benchmark scenarios for the six primary product moments;
- source-access benchmark variants, including status-only and status-open flows;
- Core Contract V0 for source status, source-open targets, guidance, request
  context, policy decisions, and context cards;
- a narrow GitHub PR metadata probe for opted-in repos;
- contract-backed terminal commands: `refresh`, `context`, `why`, and
  `open-source`;
- project config for the first demo path;
- product language docs and a scripted terminal transcript;
- a live overlapping-PR proof against public GitHub PR metadata.

Important exclusions are still intact: no comments, no review bodies, no raw
patches, no commit bodies, no author identity, no broad repo search, no LLM in
the broker, and no source body browsing by default.

## Current Sprint

Current operating plan:
[Sprint 02: Dogfood The Terminal Loop](../product/sprints/2026-06-16-sprint-02.md).

Goal: make TeamCtx usable as a real local terminal tool in an owned repository.

Sprint 02 priorities:

1. Add `teamctx init` and safe project config writing.
2. Make `context`, `why`, and `open-source` default to the local context document.
3. Dogfood the GitHub PR metadata path against an owned repo with a seeded open
   PR.
4. Update the scripted terminal demo and README to the current command shape.
5. Add one issue-tracker fixture path without claiming live Jira or Linear
   support.
6. Decide whether `open-source` should split into source-specific commands.

## MVP Track

The MVP is not a connector catalog. It is a dependable terminal loop that saves
agent/source lookup work without creating a surveillance, memory, or search
product.

MVP capabilities:

- initialize TeamCtx in a repository;
- refresh compact working context from configured sources;
- show source health when configured context is missing, stale, blocked, or
  unavailable;
- render task-changing context at agent start and resume points;
- explain why each card appears;
- open original source locations only through explicit, policy-gated actions;
- keep source bodies out of the default agent workspace;
- prove every public source claim with fixtures, failure-path tests, and source
  health behavior.

MVP source order:

1. Local workspace and request scope.
2. GitHub PR metadata for opted-in repos.
3. GitLab MR metadata after the forge-review family contract is stable.
4. Jira or Linear issue metadata through a fixture-proven work-tracker contract.
5. Confluence or governed docs through explicit links and structured rule blocks.
6. Approved local note folders, including Obsidian-style vaults, only as selected
   local sources with clear advisory/review boundaries.
7. Explicit chat handoffs only after marker, allowlist, and omission rules are
   proven in fixtures.

## Deferred Source Families

These are valuable, but not first until the dogfood loop is reliable:

- live Jira;
- live Linear;
- live Confluence;
- live Obsidian vault ingestion;
- Slack or Teams handoffs;
- broader forge providers;
- CI/deploy source health;
- read-only local API;
- optional read-only MCP server.

Deferred does not mean unimportant. It means the product must first prove that a
small, source-backed terminal packet changes real coding-agent behavior without
requiring the user to manage another knowledge system.

## Engineering Rules

- Public claims require tests.
- Core stays pure.
- Connectors are translators, not policy bypasses.
- Source text remains untrusted evidence, never instructions.
- Every card has provenance, reason, freshness, and source-health context.
- Missing context is represented honestly.
- No live connector is documented as supported until it has fixtures,
  failure-path tests, policy coverage, and source-health reporting.
- Config stores credential references, never credential values.
- Product language avoids memory, ledger, registry, promotion, surveillance, and
  productivity-tracking framing.

## Release Gates

A public release candidate needs:

- supported card kinds with golden tests;
- supported source families with conformance tests;
- malicious-input and source-health tests for supported live connectors;
- security and privacy docs matching implementation;
- README claims backed by tests;
- package build and install checks;
- no required workflow depending on developer-local credentials;
- a dogfood transcript from an owned repository.
