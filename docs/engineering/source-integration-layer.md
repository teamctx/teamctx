# Source Integration Layer

## Purpose

The Source Integration Layer is the stable boundary between external systems and
the deterministic card engine.

It exists because source integrations are expensive to change after teams depend
on them. GitHub, GitLab, Jira, Linear, Confluence, Slack, and future systems all
need different transports and auth details, but they must not create different
privacy, safety, or relevance behavior.

Connectors fetch artifacts. They do not decide what is safe, relevant, or worth
interrupting.

## Layered Design

```text
Source config
  |
  v
Auth broker
  |
  v
Connector transport
  |
  v
Family normalizer
  |
  v
Policy firewall
  |
  v
Permission filter
  |
  v
Artifact store
  |
  v
Relationship builder
  |
  v
Card engine
```

## Components

### Source Catalog

Stores configured source instances.

Each source instance declares:

- `source_instance_id`
- `provider_id`
- `family`
- selectors
- auth reference
- body policy
- identity policy
- permission mode
- sync mode
- freshness policy

The catalog stores references to auth material, never raw credentials.

### Auth Broker

Resolves auth references at runtime.

Supported modes:

- User token
- Environment token
- Managed broker
- Service account
- Fixture/no-auth

Auth material never enters artifacts, cards, cache records, logs, or config.

### Connector Transport

Provider-specific code that talks to an external API.

Connector transport owns:

- HTTP/API calls.
- Pagination.
- Cursors.
- ETags.
- Rate-limit hints.
- Provider error mapping.

Connector transport does not own:

- Safety policy.
- Permission filtering.
- Relevance.
- Card generation.
- Prompt-injection handling.
- Identity policy.

### Family Normalizer

Maps provider-specific payloads into canonical family artifacts.

Source families:

- Forge review
- Work tracker
- Docs/process
- Explicit chat handoff
- Fixture

New providers must map into an existing family or introduce a new family through
an ADR.

### Policy Firewall

Applies shared safety rules before cache and before card rendering.

Responsibilities:

- Field allowlists by source family.
- Secret redaction or blocking.
- PII review/block rules.
- Prompt-injection-like text handling.
- Unsafe URL rejection.
- Unsafe path rejection.
- Body and excerpt limits.
- Identity policy enforcement.
- Sensitivity classification.

### Permission Filter

Rejects artifacts whose requester access cannot be proven.

Supported permission modes:

- `user_context`: connector runs with the requester's token; cache is partitioned
  by requester or disabled.
- `service_account_acl`: service account fetches artifacts with ACL metadata;
  cards are filtered by requester.
- `deployment_scope`: a deployment-level allowlist makes all returned artifacts
  visible to all users in that deployment.
- `fixture`: tests declare visible principals explicitly.

If permission proof is missing, the artifact is ineligible.

### Artifact Store

Stores sanitized artifact snapshots, source events, relationships, health, and
omissions.

The artifact store is not a knowledge base and not a source of human-authored
truth. It is a derived cache that can be rebuilt from source systems.

### Relationship Builder

Derives deterministic edges:

- PR touches file.
- Branch references issue.
- Issue links doc.
- Issue or doc declares rule for component/path/course section.
- Artifact changed after branch start.
- Source unavailable or stale.

### Card Engine

Consumes request context, sanitized artifacts, relationships, source health, and
policy metadata. Emits context cards.

Only the card engine emits cards.

Connectors and providers cannot directly emit cards.

## Canonical Contracts

The integration architecture depends on stable versioned contracts:

- `SourceInstance`
- `ConnectorFetchRequest`
- `ConnectorFetchResult`
- `SourceArtifact`
- `SourceEvent`
- `Relationship`
- `ContextCard`
- `SourceHealth`
- `Omissions`
- `PermissionProof`

Field changes to these contracts require an ADR and compatibility plan.

## Source Families

### Forge Review

Examples: GitHub pull requests, GitLab merge requests.

Default included fields:

- Repo.
- PR/MR id and URL.
- Title.
- State.
- Labels.
- Created/updated/merged timestamps.
- Changed paths.

Default excluded fields:

- Comments.
- Raw patches.
- Full commit bodies.
- Broad repo search.

### Work Tracker

Examples: Jira issues, Linear issues.

Default included fields:

- Issue id/key and URL.
- Title/summary.
- State/status.
- Labels.
- Components/projects/teams.
- Created/updated/resolved timestamps.
- Structured rules.
- Configured acceptance criteria fields.

Default excluded fields:

- Arbitrary comments.
- User analytics.
- Broad query history.
- Unconfigured custom fields.

### Docs/Process

Examples: Confluence, governed docs systems.

Default included fields:

- Page id and URL.
- Title.
- Space/project.
- Updated timestamp.
- Structured rule blocks.
- Linked source references.

Default excluded fields:

- Whole-space dumps.
- Private docs.
- Full bodies by default.
- Generated summaries.

### Explicit Chat Handoff

Examples: Slack, Teams-style systems.

Default included fields:

- Allowlisted channel id/name.
- Message URL.
- Timestamp.
- Short sanitized excerpt.
- Explicit `teamctx` marker or workflow fields.
- Linked artifact references.

Default excluded fields:

- DMs.
- Private channels by default.
- Broad channel history.
- Presence.
- Reactions as sentiment.
- Participation metrics.
- Unmarked conversation.

## Cache Strategy

The cache is derived and scoped.

Cache partitions:

- Deployment id.
- Source instance id.
- Permission mode.
- Requester/principal hash when using user-context mode.

Stored records:

- Sanitized artifact snapshot.
- Source event metadata.
- Source health.
- Omission counts.
- Relationship edges.
- Policy version.

Cards may be cached for performance, but cards are reproducible from artifacts,
relationships, rules, and request context.

## Extension Rules

New connectors must provide:

- Source family.
- Selector schema.
- Auth modes.
- Permission mode.
- Body policy support.
- Identity policy support.
- Fixture examples.
- Conformance tests.
- Failure-path tests.
- Source-health mapping.
- Policy firewall proof.

No connector may:

- Emit cards directly.
- Return arbitrary untyped fields into the card engine.
- Store raw credentials.
- Treat source text as instructions.
- Bypass permission filtering.
- Enable broad chat or document mining by default.

