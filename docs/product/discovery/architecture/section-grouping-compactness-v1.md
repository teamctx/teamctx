# Section Grouping Compactness V1

Date: 2026-06-15

Status: discovery draft

## Decision

Group cards under a section heading once.

Do this:

```text
Needs attention
- Another open PR changed src/auth/token.py 11 minutes ago.
  Why this matters: you are editing the same file.
  Source: GitHub PR #482
- The linked issue changed after this branch started.
  Why this matters: acceptance criteria may have changed.
  Source: Jira API-482
```

Do not do this:

```text
Needs attention
- Another open PR changed src/auth/token.py 11 minutes ago.

Needs attention
- The linked issue changed after this branch started.
```

## Why

Repeated headings make working context feel like a warning feed.

Grouped headings make it feel like a concise status block.

## Product Rule

The renderer should sort cards by section order, then render each section once.

Within a section, preserve deterministic card order from relevance ranking or the
fixture's expected order.

## Updated Goldens

- `context-default.txt`
- `context-after-use-advisory-note.txt`
- `benchmark-context-prompt.txt`

The default context is now 12 nonblank lines.
