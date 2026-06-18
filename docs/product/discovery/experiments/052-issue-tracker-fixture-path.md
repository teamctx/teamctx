# E-052: Issue-Tracker Fixture Path

## Purpose

Prove one fixture-backed work-tracker path can normalize through Core Contract V0
and render through the terminal commands without claiming live Jira or Linear
support.

## Product Question

Can TeamCtx surface changed acceptance criteria from structured issue metadata
while keeping arbitrary issue body text and comments out of the context packet?

## Scope

Fixture:

- `docs/product/discovery/fixtures/contracts/v0/issue-tracker-acceptance-criteria-document.json`

Source-family boundary:

- `issue_tracker` structured metadata only.
- Source body is `status_only`.
- Issue body text and comments are not included.
- No live Jira or Linear connector claim.

Terminal path:

- `context --contract ...issue-tracker...`
- `why card_issue_acceptance_changed --contract ...issue-tracker...`
- `open-source card_issue_acceptance_changed --contract ...issue-tracker...`

## Pass Criteria

- The fixture round-trips through Core Contract V0.
- The card includes source, reason, freshness, confidence, and source-body status.
- Terminal rendering shows the `Needs attention` card and explains why it appears.
- `open-source` keeps the issue body unavailable/status-only.
- Tests explicitly prove comments remain outside the openable source body policy.

## Output

- `runs/2026-06-17-e052-issue-tracker-fixture-path.md`
