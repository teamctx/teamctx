# Build Plan

This file is the short sequencing overview. The operational engineering plan is
maintained in [Implementation Plan](implementation-plan.md).

## Phase 0: Foundation

Goal: establish the OSS project shape and prove the core semantics before live
connectors.

Deliverables:

- Project docs and governance.
- Python package skeleton.
- Pure core models for artifacts, relationships, cards, policy, relevance, and
  rules.
- Fixture connector.
- CLI command that reads a fixture and emits cards.
- Tests for every product claim.

Exit criteria:

- `pytest`, `ruff`, and `mypy` pass.
- Core package has no I/O imports.
- Fixture production-day scenario is deterministic.
- Cards include source, URL, reason, severity, and timestamps.

## Phase 1: Card Engine Contract

Goal: make the product useful without live integrations.

Card rules:

- Same repo and same file touched by open PR -> `overlapping_change`.
- Same repo and same file touched by merged PR after branch start ->
  `overlapping_change` with reuse/notice severity.
- Linked issue contains an explicit structured rule -> `linked_issue_rule`.
- Linked issue acceptance criteria updated after branch start ->
  `acceptance_criteria_changed`.
- Linked doc updated after branch start -> `linked_doc_changed`.
- Configured source unavailable and no successful baseline -> `source_unavailable`.

Implementation constraints:

- No LLM.
- No raw document dump in cards.
- No comments unless the fixture explicitly marks them as included.
- No identity fields unless the policy explicitly allows them.

## Phase 2: Local Cache And Server

Goal: support real workflows without adding write capabilities.

Deliverables:

- SQLite artifact cache.
- Source health table.
- Read-only local API.
- Optional read-only MCP server.
- CLI commands:
  - `teamctx status`
  - `teamctx refresh`
  - `teamctx cards`
  - `teamctx inspect artifact`
  - `teamctx policy check`

Exit criteria:

- Cache never stores secrets after policy enforcement.
- Health/freshness is visible.
- Missing context is represented honestly.

## Phase 3: Connector Family Contract

Goal: make expansion to GitHub, GitLab, Jira, Linear, Confluence, Slack,
and similar systems deliberate instead of ad hoc.

Deliverables:

- Source family contracts for forge review, work tracking, docs/process, and
  explicit chat handoff.
- Connector conformance tests.
- Fixture examples for every family.
- Family-specific default-deny field policies.
- Permission-proof and source-health requirements.

Exit criteria:

- A new vendor connector cannot bypass policy by returning arbitrary fields.
- Chat handoff connectors cannot ingest DMs, private channels by default,
  broad history, presence, sentiment, or participation analytics.

## Phase 4: GitHub Connector

Goal: support the first live source with a narrow, safe surface.

Scope:

- Opted-in repos only.
- PR metadata.
- Changed files.
- Labels.
- State.
- Created/updated/merged timestamps.
- Canonical URLs.

Excluded from this phase:

- PR comments.
- Review bodies.
- Commit patches.
- User activity feeds.
- Broad repo search.

Exit criteria:

- Connector can prove which repos and labels were selected.
- Secret scanning and URL/path sanitization run before cache.
- Tests cover malformed and malicious source text.

## Phase 5: Work Tracker Connectors

Goal: support issue-linked rules and acceptance criteria across Jira and Linear.

Scope:

- Opted-in Jira projects or Linear teams only.
- Issue key/id, summary, status, labels, components/projects, updated timestamp.
- Structured `teamctx` fields or fenced blocks for rules.
- Acceptance criteria from explicitly configured field ids.

Excluded from this phase:

- Arbitrary issue comment mining.
- User/person analytics.
- Broad JQL beyond configured selectors.

## Phase 6: Docs Connector

Goal: support linked process docs without broad document search.

Scope:

- Explicitly linked pages only.
- Space allowlists.
- Page title, URL, updated timestamp.
- Structured rules blocks.
- Section-level change hashes where APIs support them.

Excluded from this phase:

- Whole-space semantic search.
- Private docs.
- Arbitrary prose summarization.

## Phase 7: Explicit Chat Handoff Connector

Goal: support Slack or Teams-style handoffs without becoming chat mining.

Scope:

- Allowlisted channels only.
- Explicit `teamctx` marker, label, workflow, or bot mention required.
- Message URL, timestamp, channel id/name, short sanitized excerpt, and
  structured rule/handoff fields when present.

Excluded from this phase:

- DMs.
- Private channels by default.
- Broad channel history.
- Presence.
- Reactions as sentiment.
- Participation analytics.

## Phase 8: Team Preview

Goal: prove real team value while preserving the privacy boundary.

Deliverables:

- Admin opt-in config.
- Permission-aware connector mode.
- Audit log of card requests and returned card ids, without prompt logging.
- Interrupt budget configuration.
- Static inspection report for humans.

## Engineering Rules

- Public claims require tests.
- Core stays pure.
- Connectors are translators, not policy bypasses.
- Source text remains untrusted.
- Every card has provenance.
- Every denial or omission is countable.
- No live connector is documented as supported until it has fixtures, failure
  tests, and source-health reporting.

