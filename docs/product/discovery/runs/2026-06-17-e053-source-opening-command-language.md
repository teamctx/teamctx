# E-053 Run: Source-Opening Command Language

Date: 2026-06-17

## Purpose

Resolve the Sprint 02 question of whether `open-source` should split into
source-specific commands.

## Decision

Keep `teamctx open-source <card-or-source-id>` as the single MVP command. Render
the source-open target's concrete `open_label` as the terminal heading.

This makes the command stable while the output becomes source-specific:

- `Open PR`
- `Open doc status`
- `Open issue status`

Do not add `open-pr`, `open-issue`, or `open-doc` aliases yet. Split later only
if a source family needs distinct arguments, provider behavior, or safety review
copy that cannot stay clean behind one command.

## Evidence

The Core Contract already stores the user-facing label on each
`source_open_target`, so this is data-driven rather than inferred from provider
names.

PR body-available target:

```text
Open PR

GitHub PR #482

Source body available by explicit provider action.
TeamCtx did not store source text in this context document.
```

Docs status-only target:

```text
Open doc status

Confluence Release Checklist

Source body unavailable.
Reason: TeamCtx has allowed metadata for this source, but not source body text.
```

Issue status-only target:

```text
Open issue status

Jira API-482 structured fields

Source body unavailable.
Reason: TeamCtx has allowed metadata for this source, but not source body text.
```

## Product Read

The user should not need to learn a command catalog before source-family behavior
is proven. The important product distinction is not the shell verb; it is whether
the selected source can return body text, status only, or nothing. Target labels
communicate that distinction without widening the CLI.

## Verification

```bash
python3 -m pytest tests/test_contract_terminal.py -q
python3 -m ruff check src/teamctx/contract_render.py tests/test_contract_terminal.py
```

Result: both focused checks passed.
