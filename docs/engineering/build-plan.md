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

## Current Milestone

The **[Thesis-Complete Engine milestone](../product/sprints/2026-06-19-milestone-thesis-complete-engine.md)
is DONE** (merged to `main`): the v1.0-paper core, the four-kind registry, thin authority,
and replay/explainability are real in code (T1/T2/T5/S2 embodied). **Two connectors are live**
— collision (GitHub PRs) and doc-superseded (declared frontmatter); the latter merged
2026-06-20.

The active forward plan is now the
**[Product Completion plan](../product/sprints/2026-06-21-product-completion-plan.md)**:
we built the credibility *because*; now we build the *marquee* (timely, ambient team context).
That doc records the **decided-vs-built gap** — the engine targets the certifiable ~38%
slice on 2 of ~7 sources, while the ambient **L tier (43%) is an empty reserved channel** and
Jira/Confluence/GitLab/Slack/MCP are decided-but-unbuilt.

Immediate next: **Phase 0** — prove the current vertical (the doc-superseded dogfood), then
**Phase 1** — feed the two dormant engine kinds via connectors (missed-gate ← GitHub
check-runs; criteria-changed ← Jira), the cheapest path to marquee breadth.

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
