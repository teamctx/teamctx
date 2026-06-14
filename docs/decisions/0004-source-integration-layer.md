# ADR 0004: Source Integration Layer

- Status: accepted
- Date: 2026-06-14

## Context

`teamctx` needs to support multiple source systems: GitHub, GitLab, Jira,
Linear, Confluence, Slack, and likely others. Adding each connector directly to
the card engine would make safety, permission, body-policy, and relevance
behavior inconsistent and expensive to change.

The costly decision is the integration boundary, not any one connector.

## Decision

`teamctx` has a first-class Source Integration Layer between external systems
and the card engine.

Connectors fetch provider data. Family normalizers map provider data into
canonical artifacts. A shared policy firewall, permission filter, artifact store,
relationship builder, and card engine own safety and relevance.

Providers cannot emit context cards directly.

Source families are:

- Forge review.
- Work tracker.
- Docs/process.
- Explicit chat handoff.
- Fixture.

New providers must map into a family contract or introduce a new family through
an ADR.

## Consequences

- GitHub, GitLab, Jira, Linear, Confluence, Slack, and future connectors share
  the same safety and card-generation path.
- Connector code remains transport-specific and does not become a policy bypass.
- Chat integrations can exist without becoming chat mining.
- Permission proof and source health become required connector outputs.
- Contract changes require deliberate versioning and migration.

