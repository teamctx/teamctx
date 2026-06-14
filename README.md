# teamctx

Deterministic ambient context for software teams.

`teamctx` is a non-agentic, non-generative context broker for shared engineering
work. It watches approved work artifacts such as pull requests, issues, docs,
explicit chat handoffs, and release/process records, then produces small, sourced
context cards when a
developer or coding agent needs to know something.

It does not monitor people. It does not read private messages. It does not use an
LLM to infer intent. It does not write to source systems by default.

## Product Thesis

Teams already put important facts in GitHub, GitLab, Jira, Confluence, and other
systems of record. The problem is that those facts are scattered, noisy, and
usually discovered too late.

`teamctx` makes useful team context ambient:

- An overlapping pull request changed the same file.
- A linked Jira issue added a constraint.
- A process document changed after the branch started.
- A source artifact is unavailable, so absence of context is not a green light.

Every card is deterministic, source-backed, permission-aware, and explainable.

## Non-Goals

- No LLM.
- No agent runtime.
- No autonomous action.
- No broad enterprise search.
- No productivity analytics.
- No presence tracking.
- No private chat, email, or DM ingestion.
- No sentiment, performance, or people summaries.

## First Interfaces

```bash
teamctx status
teamctx cards --repo org/app --branch feature/foo --path src/auth/token.py
teamctx fixtures smoke docs/fixtures/production-day.json
teamctx serve
```

Example card:

```json
{
  "kind": "overlapping_change",
  "severity": "warning",
  "message": "Open PR #482 changed src/auth/token.py 11 minutes ago.",
  "source_url": "https://github.com/org/app/pull/482",
  "reason": "same repo and same file path",
  "updated_at": "2026-06-14T16:20:00Z"
}
```

## Project Contract

`teamctx` is built around a deterministic, fixture-first contract: normalize
approved artifacts, enforce policy, derive relationships, and return sourced
context cards. Connector families cover forge reviews, work trackers, docs/process systems,
and explicit chat handoffs. Live connectors only become supported surfaces after
fixtures, failure-path tests, and source-health behavior prove the same contract.

See:

- [Product Brief](docs/product/product-brief.md)
- [Product Plan](docs/product/product-plan.md)
- [Architecture](docs/engineering/architecture.md)
- [Source Integration Layer](docs/engineering/source-integration-layer.md)
- [Build Plan](docs/engineering/build-plan.md)
- [Security And Privacy](docs/engineering/security-privacy.md)
- [Quality Bar](docs/engineering/quality-bar.md)

