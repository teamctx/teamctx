# E-053: Source-Opening Command Language

## Purpose

Decide whether Sprint 02 should split `teamctx open-source` into source-specific
commands now that PR, docs, and issue fixture targets exist.

## Product Question

Should TeamCtx expose separate commands like `open-pr`, `open-issue`, and
`open-doc`, or keep one command while rendering source-specific action labels?

## Scope

Inputs:

- Core Contract V0 source-open targets already carry `open_label`.
- Existing fixtures include `Open PR`, `Open doc status`, and `Open issue status`.
- Live source support remains narrow: GitHub PR metadata only, with Jira/Linear
  still fixture-only.

Out of scope:

- Adding live Jira, Linear, or Confluence connectors.
- Opening source bodies by default.
- Adding command aliases before source families need different behavior.

## Pass Criteria

- Keep the CLI command set small for MVP.
- Render source-specific action language in terminal output.
- Preserve status-only behavior for docs and issue metadata.
- Tests cover PR, doc-status, and issue-status labels.

## Output

- `runs/2026-06-17-e053-source-opening-command-language.md`
