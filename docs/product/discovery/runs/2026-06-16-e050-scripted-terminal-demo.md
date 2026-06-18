# E-050 Run: Scripted Terminal Demo

Date: 2026-06-16

## Purpose

Capture the first CPO-demoable terminal flow for Sprint 01.

## Setup

Example project config:

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

## Demo Path A: Configured Source Unavailable

Command:

```bash
teamctx refresh --path src/auth/token.py --task "Update token rotation"
```

Expected result when `GITHUB_TOKEN` is not set:

```text
Refreshed context at .teamctx/context.json
```

Then:

```bash
teamctx context --contract .teamctx/context.json
```

Expected shape:

```text
Working context

No working context for this task.

Source status
- GitHub PR metadata is unavailable because no token is configured.
  Source: GitHub org/app
```

Product read: missing configured context is visible as source status, not silent
confidence.

## Demo Path B: Fixture-Backed Collision Context

Command:

```bash
teamctx context --contract docs/product/discovery/fixtures/contracts/v0/core-contract-document.json
```

Expected shape:

```text
Working context

Needs attention
- Another open PR changed src/auth/token.py 11 minutes ago.
  Why this matters: you are editing the same file.
  Source: GitHub PR #482

Project guidance
- Token rotation must preserve compatibility for legacy clients.
  Why this matters: this applies to auth-service token changes.
  Source: approved project guidance, originally from Jira API-482
```

Then:

```bash
teamctx why card_pr_collision --contract docs/product/discovery/fixtures/contracts/v0/core-contract-document.json
```

Expected shape:

```text
Show why

This appears because same repository and file path as the current task.

Source: GitHub PR #482
Freshness: fresh
Scope: auth-service, src/auth/token.py
Confidence: high
Source body: available only by explicit source-open action
Agent visibility: shown as evidence to verify before relying
```

Then:

```bash
teamctx open-source card_stale_docs --contract docs/product/discovery/fixtures/contracts/v0/core-contract-document.json
```

Expected shape:

```text
Open doc status

Confluence Release Checklist

Source body unavailable.
Reason: TeamCtx has allowed metadata for this source, but not source body text.
```

## Remaining Demo Gap

Run the GitHub probe against an opted-in real repo with credentials and at least
one open PR touching the demo path. The terminal path is ready; the live-data
proof still needs a real overlapping PR fixture or repository state.
