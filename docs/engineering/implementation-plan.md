# Implementation Plan

## Purpose

This document is the operating build plan for `teamctx`.

It complements the product plan, architecture, source integration layer, and
short build-plan overview. The implementation follows one rule throughout:
source-backed ambient context is useful only when the safety, permission, and
provenance boundaries are part of the product contract, not features added around
the edges.

Sequencing in this plan reflects engineering dependency order. It does not define
a weaker product tier. Every completed surface must satisfy the same privacy,
security, determinism, and test standards.

## Non-Negotiable Constraints

- The broker is deterministic.
- The broker does not use an LLM.
- The broker does not act as an agent runtime.
- Source text is untrusted evidence, never instruction text.
- Approved artifacts are the input boundary; people are not observed.
- Permission checks happen before relevance checks.
- Policy enforcement happens before cache writes and card rendering.
- Connectors fetch and normalize artifacts; they do not emit cards.
- Cards are the primary output.
- Cards contain provenance, reasons, freshness, and omission metadata.
- Missing or stale source data is represented explicitly.
- Auth material never enters artifacts, cards, caches, fixtures, logs, or errors.
- Live connector support is not documented until fixtures, conformance tests,
  malicious-input tests, and source-health behavior exist.

## Core Product Flow

```text
Source config
  -> auth broker
  -> connector transport
  -> family normalizer
  -> policy firewall
  -> permission filter
  -> artifact store
  -> relationship builder
  -> card engine
  -> CLI / API / optional read-only MCP surface
```

The policy firewall and permission filter are mandatory boundaries. No source
family, provider connector, cache path, CLI command, API route, or MCP surface may
skip them.

## Contract Freeze

The first durable engineering milestone is a versioned contract set. These
contracts are the stable boundary for internal code, fixtures, connector authors,
and downstream consumers.

Required contracts:

- `SourceInstance`
- `AuthReference`
- `ConnectorFetchRequest`
- `ConnectorFetchResult`
- `SourceArtifact`
- `SourceEvent`
- `Relationship`
- `RequestContext`
- `ContextCard`
- `SourceHealth`
- `Omissions`
- `PermissionProof`
- `PolicyDecision`
- `PolicyConfig`

Contract requirements:

- Every externally serialized object includes a `contract_version`.
- Pydantic validates boundary input and output.
- Rule evaluation operates on validated objects.
- Timestamps are timezone-aware UTC.
- URLs are normalized and validated before card output.
- File paths are normalized as repository-relative strings.
- Enums are closed in tests, with explicit compatibility notes when extended.
- Unknown fields from source systems are dropped unless family policy allows
  them.
- Breaking field changes require an ADR and fixture migration.

Acceptance criteria:

- Golden contract fixtures exist for every contract.
- Invalid fixtures fail with useful validation errors.
- Contract tests prove unknown fields cannot bypass policy.
- Serialization round trips preserve card ids, source urls, reasons, timestamps,
  safety metadata, and omission counts.

## Package Boundaries

Target package shape:

```text
src/teamctx/
  core/
    artifacts.py
    relationships.py
    cards.py
    contracts.py
    policy.py
    relevance.py
    rules.py
    scope.py
    time.py
  connectors/
    base.py
    families.py
    fixtures.py
    github.py
    gitlab.py
    jira.py
    linear.py
    confluence.py
    slack.py
  store/
    sqlite.py
    migrations/
  cli/
    main.py
  server/
    api.py
    mcp.py
```

Boundary rules:

- `teamctx.core` has no filesystem, network, subprocess, randomness, or current
  time reads.
- `teamctx.connectors` may perform source I/O but cannot decide safety,
  relevance, interruption, or card wording.
- `teamctx.store` stores only sanitized artifacts and derived metadata.
- `teamctx.cli` and `teamctx.server` are orchestration surfaces.
- Optional dependencies are grouped by surface and connector family.

## Workstream 1: Repository And Release Engineering

Deliverables:

- GitHub Actions for tests, type checks, linting, packaging, and docs link
  checks.
- PyPI Trusted Publishing release workflow.
- Coverage enforcement.
- Dependency review and license checks.
- `ruff`, `mypy --strict`, `pytest`, and `git diff --check` in CI.
- Release checklist that validates public claims against tests.
- Issue and PR templates for bugs, connectors, security-adjacent reports, and
  docs changes.

Acceptance criteria:

- A clean checkout can run the documented development commands.
- CI fails on formatting, typing, tests, or coverage regressions.
- Builds produce valid sdist and wheel artifacts.
- Release publishing does not require a long-lived PyPI token in CI.
- Security-sensitive reports route through the documented security policy.

## Workstream 2: Core Contracts And Pure Domain Model

Deliverables:

- Versioned models for artifacts, relationships, request context, cards,
  source health, omissions, permissions, and policy decisions.
- Stable id generation for artifacts, relationships, and cards.
- Deterministic time helpers that require injected clocks.
- Core purity tests.

Acceptance criteria:

- The core package has no I/O imports.
- Card ids are stable for equivalent inputs.
- All externally visible models have JSON schema coverage.
- Every card can answer: what source produced this, why is it relevant, when was
  it detected, what was omitted, and what safety classification applies?

Required tests:

- Contract validation tests.
- Golden serialization tests.
- Core import purity tests.
- Stable id tests.
- Timezone handling tests.

## Workstream 3: Policy Firewall

Deliverables:

- Family-specific field allowlists.
- Secret and credential-pattern detection.
- PII and sensitive-content detection rules.
- Personnel, performance, sentiment, and coworker-opinion block rules.
- Prompt-injection-like text classification.
- URL and path safety validation.
- Text length limits and excerpt policy.
- Redact, block, quarantine, and omit outcomes.
- Omission counters by reason.

Acceptance criteria:

- Policy runs before cache writes.
- Blocked content never appears in cards, logs, cache rows, or errors.
- Redacted content cannot reconstruct the original sensitive value.
- Prompt-injection-like source text is never rendered as an instruction.
- Identity fields are absent unless identity policy explicitly allows them.
- Every policy decision is explainable without leaking blocked content.

Required tests:

- Property tests for credential-shaped strings.
- Malicious source text fixtures.
- Unsafe URL and path fixtures.
- Personnel/performance judgment fixtures.
- Oversized body fixtures.
- Per-family allowlist tests.
- Cache safety tests proving raw unsafe values are not stored.

## Workstream 4: Fixture System

Deliverables:

- Fixture file format and JSON schema.
- No-network fixture connector.
- Fixture validator.
- Golden production-day scenario.
- Malicious-input fixture suite.
- Permission and source-health fixture suite.

Required fixture scenarios:

- Open PR overlaps the current work path.
- Merged PR touched the same path after branch start.
- Linked issue provides a structured rule.
- Linked issue acceptance criteria changed after branch start.
- Linked doc changed after branch start.
- Configured source has no successful refresh baseline.
- Configured source is stale.
- Artifact is blocked by policy.
- User lacks permission proof.
- Slack-style handoff is marked and allowed.
- Slack-style handoff is unmarked and ignored.
- DM/private-channel chat artifact is rejected.
- Source text contains secret-shaped content.
- Source text contains prompt-injection-like content.
- Source text contains coworker performance commentary.

Acceptance criteria:

- Fixture cards are deterministic across repeated runs.
- Fixtures cover every public product example.
- Fixtures cover every supported source family.
- Fixtures can run in CI without network credentials.
- Golden output changes require intentional review.

## Workstream 5: Relationship Builder

Deliverables:

- Path overlap relationships.
- Branch-to-issue relationships.
- Issue-to-doc relationships.
- Component, project, path, and course-section rule relationships.
- Changed-after relationships.
- Source health relationships.

Acceptance criteria:

- Relationship derivation is deterministic and side-effect free.
- Relationship reasons are human-readable and machine-testable.
- Path matching does not allow traversal or absolute path confusion.
- Ambiguous links produce lower-confidence relationships or omissions instead of
  fabricated certainty.

Required tests:

- Path normalization tests.
- Branch issue-key extraction tests.
- Linked-doc extraction tests from structured fields.
- Changed-after timestamp tests.
- Ambiguous relationship tests.

## Workstream 6: Card Engine And Relevance

Deliverables:

- Card rule engine.
- Card kinds:
  - `overlapping_change`
  - `linked_issue_rule`
  - `acceptance_criteria_changed`
  - `linked_doc_changed`
  - `source_unavailable`
  - `policy_blocked_artifact`
  - `stale_context`
- Deterministic ranking.
- Dedupe rules.
- Severity vocabulary.
- Interrupt budget policy.
- Pull-based and interrupt-eligible card modes.

Acceptance criteria:

- Cards are broker-authored facts, not source-text summaries.
- Relevance uses request context, relationships, timestamps, source health, and
  policy metadata.
- Interrupt-eligible cards are limited to high-signal, source-backed facts.
- Low-confidence or missing evidence produces omissions or source-health cards,
  not speculative advice.
- Golden card tests cover message, reason, severity, source URL, timestamps,
  applies-to fields, safety fields, and omissions.

Card acceptance matrix:

| Card kind | Required evidence | Primary denial case |
| --- | --- | --- |
| `overlapping_change` | Same repo and path, open PR/MR or changed-after merged PR/MR | requester cannot access source artifact |
| `linked_issue_rule` | Linked issue and structured rule field/block | rule is unstructured prose only |
| `acceptance_criteria_changed` | Linked issue and configured acceptance field updated after branch start | acceptance field is not configured |
| `linked_doc_changed` | Explicit linked doc updated after branch start | doc is not linked or not permissioned |
| `source_unavailable` | Configured source has failed/no refresh baseline | source is not configured for request scope |
| `policy_blocked_artifact` | Artifact eligible by scope but blocked by policy | omission would leak blocked content |
| `stale_context` | Last successful refresh is older than freshness policy | stale source is outside request scope |

## Workstream 7: Local Store And Source Health

Deliverables:

- SQLite cache for sanitized artifacts, relationships, source events, omissions,
  and source health.
- Migration table and migration runner.
- Cache partitioning strategy for permission modes.
- Cursor and freshness metadata.
- Store inspection utilities.

Acceptance criteria:

- Raw source payloads are not stored.
- Policy-blocked fields are not stored.
- Cache rows include enough provenance to rebuild card evidence.
- Source health distinguishes unavailable, unauthorized, rate-limited, stale,
  empty, and successful states.
- Cache can be deleted and rebuilt from sources.

Required tests:

- Migration tests.
- Store round-trip tests.
- Secret-not-stored tests.
- Permission partition tests.
- Source-health state tests.

## Workstream 8: CLI, API, And Read-Only Agent Surface

Deliverables:

- CLI commands:
  - `teamctx status`
  - `teamctx refresh`
  - `teamctx cards`
  - `teamctx inspect artifact`
  - `teamctx inspect source`
  - `teamctx policy check`
  - `teamctx fixtures validate`
  - `teamctx fixtures run`
- Read-only local JSON API.
- Optional read-only MCP server.
- Stable JSON output mode.
- Human-readable output mode.
- Exit-code contract.

Acceptance criteria:

- CLI and API cannot write to source systems.
- CLI output never includes auth material or blocked source content.
- JSON output uses the same contract models as core.
- MCP tools expose cards and inspections only; they do not expose prompts,
  source bodies, arbitrary search, writes, or connector credentials.
- Every command has fixture-backed tests.

## Workstream 9: Source Integration SDK And Conformance

Deliverables:

- Connector base interface.
- Source family contracts.
- Auth broker interface.
- Permission-proof interface.
- Family normalizers.
- Connector conformance test harness.
- Provider error mapping.
- Rate-limit and pagination behavior.

Acceptance criteria:

- A connector cannot return arbitrary fields directly to the store.
- A connector cannot emit cards.
- A connector cannot mark artifacts permissioned without proof.
- Conformance tests are reusable by first-party and third-party connectors.
- New source families require an ADR.

Required conformance tests:

- Scope selector enforcement.
- Field allowlist enforcement.
- Permission proof present.
- Source health on API failure.
- Pagination/cursor behavior.
- Malformed provider payload behavior.
- Policy firewall integration.

## Workstream 10: Forge Review Connectors

Providers:

- GitHub.
- GitLab.

Included fields:

- Repo.
- PR/MR id and URL.
- Title.
- State.
- Labels.
- Created, updated, and merged timestamps.
- Changed paths.

Excluded fields:

- Comments.
- Review bodies.
- Raw patches.
- Full commit bodies.
- User activity feeds.
- Broad repository search.

Acceptance criteria:

- Repos are explicitly opted in.
- Optional label selectors are enforced.
- Changed paths are sanitized before storage.
- Source health records rate limits, auth failures, and provider errors.
- Malicious title/body text cannot become an instruction or leak unsafe content.
- Permissions are enforced through `user_context`, `service_account_acl`, or
  `deployment_scope`.

## Workstream 11: Work Tracker Connectors

Providers:

- Jira.
- Linear.

Included fields:

- Issue id/key and URL.
- Title or summary.
- State/status.
- Labels.
- Components, projects, or teams.
- Created, updated, and resolved timestamps.
- Structured `teamctx` rules.
- Configured acceptance-criteria fields.

Excluded fields:

- Arbitrary comments.
- Broad query history.
- User analytics.
- Unconfigured custom fields.

Acceptance criteria:

- Projects or teams are explicitly opted in.
- Jira JQL or Linear filters are generated only from configured selectors.
- Acceptance criteria come only from configured fields.
- Rule extraction requires structured blocks or fields.
- Arbitrary prose does not become a rule.
- User/person metadata is omitted unless identity policy allows it.

## Workstream 12: Docs And Process Connectors

Providers:

- Confluence.
- Additional governed docs systems that can satisfy the docs/process family
  contract.

Included fields:

- Page id and URL.
- Title.
- Space or project.
- Updated timestamp.
- Structured rule blocks.
- Linked source references.
- Section-level change hashes when provider APIs support them.

Excluded fields:

- Whole-space dumps.
- Private docs.
- Full bodies by default.
- Generated summaries.
- Broad semantic search.

Acceptance criteria:

- Pages are explicitly linked or selected by narrow allowlist.
- Full document text is not sent to cards.
- Structured rule blocks are parsed deterministically.
- Changed-after checks work without summarizing the page.
- Permission proof exists for every page-derived card.

## Workstream 13: Explicit Chat Handoff Connectors

Providers:

- Slack.
- Teams-style systems that can satisfy the explicit chat handoff family
  contract.

Included fields:

- Allowlisted channel id/name.
- Message URL.
- Timestamp.
- Explicit `teamctx` marker, workflow, label, or bot mention.
- Short sanitized excerpt when policy allows it.
- Structured handoff or rule fields when present.

Excluded fields:

- DMs.
- Private channels by default.
- Broad channel history.
- Presence.
- Reactions as sentiment.
- Participation analytics.
- Unmarked messages.

Acceptance criteria:

- Chat connectors cannot operate without channel allowlists.
- Unmarked messages are ignored.
- DMs and private channels are rejected by default.
- Message authors are omitted unless identity policy allows them.
- The connector cannot answer broad questions about channel history.
- The handoff card links to the source message and records omissions.

## Workstream 14: Configuration, Scope, And Admin Controls

Deliverables:

- `teamctx.yaml` schema.
- Source catalog.
- Scope selectors by repo, project, team, doc space, channel, label, and marker.
- Body policy and identity policy configuration.
- Freshness and interrupt budget configuration.
- Local mutes.
- Static inspection report.

Acceptance criteria:

- Configuration is explicit and default-deny.
- Misconfiguration fails closed.
- Users can inspect why a source, artifact, field, or card is eligible.
- Local mutes suppress cards without changing source data.
- Admin inspection reports omit secrets and blocked content.

## Workstream 15: Audit And Operations

Deliverables:

- Audit log schema.
- Source refresh logs without raw source bodies.
- Card request logs without prompts.
- Returned card-id logs.
- Health and freshness reporting.
- Error taxonomy.

Acceptance criteria:

- Audit logs never store prompts, agent responses, secrets, raw source bodies, or
  blocked content.
- Operators can answer which source produced a card and why.
- Operators can distinguish no context from unavailable context.
- Error messages are useful without leaking sensitive payloads.

## Workstream 16: OSS Contributor Experience

Deliverables:

- Connector author guide.
- Source family checklist.
- Policy checklist.
- Fixture contribution guide.
- ADR template.
- Public claim checklist.
- Compatibility policy.

Acceptance criteria:

- A contributor can add a connector by implementing the connector interface,
  family normalizer, fixtures, and conformance tests.
- A connector PR cannot pass CI without policy and permission coverage.
- Documentation states support level accurately.
- The public README does not overclaim incomplete surfaces.

## Implementation Sequence

1. Lock the contract models and JSON schema tests.
2. Build the policy firewall before any persistent cache.
3. Build fixture ingestion and golden card generation.
4. Implement relationship derivation and the first card rules.
5. Add CLI fixture commands and stable JSON output.
6. Add SQLite cache and source-health behavior.
7. Add read-only API and optional read-only MCP surface.
8. Add connector SDK and conformance tests.
9. Add forge review connectors.
10. Add work tracker connectors.
11. Add docs/process connectors.
12. Add explicit chat handoff connectors.
13. Add admin inspection, audit, and deployment hardening.
14. Prepare public release artifacts and support documentation.

Each step requires passing tests, documentation updates, and claim review before
the next source surface is presented as supported.

## Definition Of Done For Any Feature

- The behavior is deterministic.
- The behavior has fixture coverage.
- The behavior has failure-path coverage.
- Source text remains untrusted.
- Permission behavior is explicit.
- Policy behavior is explicit.
- Omission behavior is countable.
- Source health behavior is represented.
- Public docs match the implementation.
- `pytest`, `ruff`, `mypy --strict`, and `git diff --check` pass.

## Release Gates

A release is eligible only when:

- Supported card kinds have golden tests.
- Supported source families have conformance tests.
- Supported live connectors have malicious-input and source-health tests.
- Security and privacy docs match implementation.
- README claims are backed by tests.
- Package build and install checks pass.
- The release workflow uses Trusted Publishing.
- No required workflow depends on developer-local credentials.

## Open Engineering Decisions

The following decisions need ADRs before implementation reaches the affected
surface:

- Public compatibility policy for contract versions.
- Local API transport and authentication posture.
- Optional MCP package boundary and dependency strategy.
- Cache partitioning rules for `user_context` permission mode.
- Connector dependency packaging strategy.
- Supported deployment shapes for team use.
- Audit retention and rotation defaults.
