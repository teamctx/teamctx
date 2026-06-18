# E-052 Run: Issue-Tracker Fixture Path

Date: 2026-06-17

## Purpose

Add one issue-tracker fixture path for changed acceptance criteria while keeping
live Jira and Linear connectors out of scope.

## Fixture

```text
docs/product/discovery/fixtures/contracts/v0/issue-tracker-acceptance-criteria-document.json
```

The fixture models Jira `API-482` as structured issue metadata:

- source family: `issue_tracker`
- card: `card_issue_acceptance_changed`
- source body: `status_only`
- open target: `open_issue_api_482_status`
- issue body text and comments: excluded by policy

## Context Output

```text
Working context

Needs attention
- API-482 acceptance criteria changed after this branch started.
  Why this matters: token rotation retry behavior may need to follow the updated structured criteria.
  Source: Jira API-482 structured fields
```

## Why Output

```text
Show why

This appears because linked issue API-482 has structured acceptance criteria updated after branch start.

Source: Jira API-482 structured fields
Freshness: fresh
Scope: auth-service
Confidence: high
Source body: not shown; only status and allowed metadata are available
Agent visibility: shown as evidence to verify before relying
```

## Open Source Output

```text
Open issue status

Jira API-482 structured fields

Source body unavailable.
Reason: TeamCtx has allowed metadata for this source, but not source body text.
```

## Verification

```bash
python3 -m pytest tests/test_core_contracts.py tests/test_contract_terminal.py -q
python3 -m ruff check tests/test_core_contracts.py tests/test_contract_terminal.py
```

Result: both focused checks passed.

## Decision

Workstream 4 has a first fixture-backed issue path. TeamCtx can represent changed
acceptance criteria from allowed structured issue metadata, render it through the
existing terminal commands, and keep arbitrary issue comments/body text out of
the source-open path. This does not claim live Jira or Linear support.
