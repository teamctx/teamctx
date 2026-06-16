# E-051 Run: Live GitHub Overlap Probe

Date: 2026-06-16

## Purpose

Prove that the GitHub PR metadata probe can produce a real overlapping-work card
from live GitHub metadata.

## Probe Target

The TeamCtx repo had no open PRs at run time, so it could not prove collision
card generation. For a non-mutating live probe, we used the public `cli/cli` repo
and selected a path from an existing open PR.

Open PR observed before the probe:

```text
cli/cli PR #13673 touches pkg/cmd/secret/set/set.go
```

## Command

```bash
env PYTHONPATH=src TEAMCTX_LIVE_GITHUB_TOKEN="$(gh auth token)" \
  python3 -m teamctx.cli refresh \
  --github-repo cli/cli \
  --path pkg/cmd/secret/set/set.go \
  --task "Check live overlapping PR metadata" \
  --token-env TEAMCTX_LIVE_GITHUB_TOKEN \
  --output /tmp/teamctx-live-overlap-context.json
```

## Context Output

```text
Working context

Needs attention
- Open PR #13673 changed pkg/cmd/secret/set/set.go.
  Why this matters: you are editing the same file.
  Source: GitHub PR #13673
```

## Why Output

```text
Show why

This appears because same repository and file path as the current task.

Source: GitHub PR #13673
Freshness: fresh
Scope: cli/cli, pkg/cmd/secret/set/set.go
Confidence: high
Source body: not shown; only status and allowed metadata are available
Agent visibility: shown as evidence to verify before relying
```

## Open Source Output

```text
Open source

GitHub PR #13673

Source body unavailable.
Reason: TeamCtx has allowed metadata for this source, but not source body text.
```

## Contract Summary

The live contract document contained:

- `schema_version`: `teamctx.core_contract_document.v0`
- `repo`: `cli/cli`
- `source_signals`: `1`
- `context_cards`: `1`
- `source_open_targets`: `1`
- source body state: `status_only`

## Decision

Workstream 3 acceptance is satisfied for the first live source-family probe:
configured GitHub PR metadata can produce an overlapping-file context card, and
the source body remains closed by default.
