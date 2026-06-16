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

## First Runnable Slice

The current prototype is terminal-first. Configure one GitHub repo, refresh local
context, then render it before an agent starts risky work.

Example `.teamctx/config.json`:

```json
{
  "schema_version": "teamctx.project_config.v0",
  "github": {
    "repo": "org/app",
    "token_env": "GITHUB_TOKEN",
    "include_title": false
  },
  "default_output": ".teamctx/context.json"
}
```

Commands:

```bash
teamctx refresh --path src/auth/token.py --task "Update token rotation"
teamctx context --contract .teamctx/context.json
teamctx why card_github_pr_482_collision --contract .teamctx/context.json
teamctx open-source card_github_pr_482_collision --contract .teamctx/context.json
```

The GitHub probe is intentionally narrow. It reads open PR metadata and changed
file paths only. It does not read comments, review bodies, raw patches, commit
bodies, author identity, or broad repository search results. If access is
missing, `teamctx` writes source status instead of treating missing context as
confidence.

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
- [Implementation Plan](docs/engineering/implementation-plan.md)
- [Security And Privacy](docs/engineering/security-privacy.md)
- [Quality Bar](docs/engineering/quality-bar.md)

