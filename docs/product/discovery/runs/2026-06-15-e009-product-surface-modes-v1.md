# E-009 Run: Product Surface Modes V1

Date: 2026-06-15

Purpose: classify which product facts belong in the normal terminal context,
which belong behind explanation, and which belong in source settings.

## Surface 1: Working Context

What it is:

- The small block shown automatically at start/resume when there is task-changing
  context.
- Also available on request when the user asks what matters for this task.

Allowed content:

- Overlapping work that affects current files or branch.
- Changed acceptance criteria or linked issue changes.
- Saved guidance that matches repo/task scope.
- Stale or unavailable configured sources when absence would be misleading.
- Eligible explicit handoffs that match the current task.
- Advisory approved vault/doc notes only when scoped and likely useful.

Not allowed content:

- Private/local note matches.
- Slack DMs or unmarked chat.
- Unknown connector fields.
- Inaccessible artifact titles/URLs.
- Raw source bodies unless explicitly opened.
- Long summaries.

Example:

```text
Working context

Needs attention
- The linked Jira issue changed after this branch started.
  Why this matters: acceptance criteria may have changed.
  Source: Jira API-482

Saved for this project
- Token rotation must preserve compatibility for legacy clients.
  Source: approved project guidance
```

Risk:

- `Saved for this project` still may sound storage-like.

## Surface 2: Explain / Show Why

What it is:

- On-demand explanation for a shown context item.
- Trust, scope, freshness, source, and whether the agent can rely on it.

Allowed content:

- Why it matched this task.
- Source id/link if permissioned.
- Freshness and source status.
- Whether it is source-backed, advisory, stale, or approved guidance.
- What action changed session visibility.

Not allowed content:

- Internal nouns unless unavoidable.
- Blocked sensitive details.
- Inaccessible artifact identity.

Example:

```text
Why this appeared
- Scope matched: auth-service
- Source matched: Jira API-482
- Freshness: updated today
- Status: source-backed, verify before relying
- Agent visibility: available in this session
```

Risk:

- Explanation can drift into implementation vocabulary.

## Surface 3: Source Health / Settings

What it is:

- On-demand or admin-oriented source status.
- Setup, access, field allowlists, excluded paths, refresh failures, and source
  configuration.

Allowed content:

- Configured source status.
- Aggregate omitted counts when safe.
- Excluded folders/classes, not specific private matches.
- Refresh errors without raw provider diagnostics.
- Settings actions.

Not allowed content:

- Normal task cards unless they affect confidence.
- Private item titles/paths.
- DMs/unmarked chat details.
- Raw errors containing auth or provider payloads.

Example:

```text
Source status
- GitHub: fresh
- Jira: unavailable, no successful refresh yet
- Obsidian: configured folders only; private/local paths excluded
- Slack: explicit handoffs only from approved channels
```

Risk:

- If surfaced too often, this becomes an admin dashboard inside the workflow.

## Surface 4: Never Show

Content that should not appear in any normal product surface:

- Slack DM matches.
- Private/personal note matches.
- Secrets or credential-shaped text.
- Prompt-injection-like source instructions.
- Inaccessible artifact titles, URLs, or excerpts.
- Unknown connector field values.
- Presence, productivity, sentiment, or participation signals.

## Classification Table

| Fact type | Working context | Show why | Source settings | Never show |
| --- | --- | --- | --- | --- |
| Same-file PR overlap | yes | yes | no | no |
| Changed linked issue | yes | yes | no | no |
| Safety-blocked issue body | limited | limited | aggregate | exact pattern/content |
| Stale configured doc | yes if scoped | yes | yes | stale body as guidance |
| Inaccessible linked doc | aggregate if scoped | aggregate | yes | title/url/body |
| Private vault note match | no | no | aggregate only | title/path/body |
| Obsidian approved folder note | maybe | yes | yes | no |
| Slack marked handoff | maybe | yes | yes | surrounding history |
| Slack DM/unmarked message | no | no | no | details/existence |
| Unknown connector field | no | no | aggregate/settings | value |
| Saved guidance match | yes | yes | no | no |

## Findings

TeamCtx likely needs a command/surface distinction like:

- automatic `Working context`
- on-demand `Show why`
- on-demand/admin `Source status`

But these should not be sold as user vocabulary. They are product surfaces.
The everyday developer mostly sees the first one and only touches the others
when trust or setup matters.

## Decision

Adopt three-surface model for experiments:

1. Working context.
2. Show why.
3. Source status/settings.

Keep `Never show` as a first-class safety category.
