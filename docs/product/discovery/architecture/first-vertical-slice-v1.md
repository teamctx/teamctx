# First Vertical Slice V1

Date: 2026-06-15

Status: discovery draft

## Slice Name

Issue-backed file edit with changed context.

## User Story

A developer starts or resumes an agent terminal on a branch tied to an issue.
Before the agent edits files, TeamCtx shows only the working context that could
change the next action.

## Demo Task

```text
Update src/auth/token.py to add token rotation retry handling for API-482.
```

## Sources In Scope

| Source | Role | Required for first slice? |
| --- | --- | --- |
| Local git workspace | branch, dirty tree, changed files, branch start point | yes |
| Git hosting metadata | open PR/MR touching same file | yes, fixture or real API |
| Issue tracker metadata | issue changed after branch start | yes, fixture or real API |
| Source status | stale/unavailable/blocked caveats | yes, at least fixture |
| Project guidance | active reviewed guidance if present | optional but valuable |

## Sources Out Of Scope

- Chat.
- Email.
- Calendar.
- Broad docs search.
- Private notes.
- Activity analytics.

## First User Flow

1. User starts an agent session in a repo.
2. TeamCtx detects repo, branch, and likely issue key from branch name, commit,
   or task text.
3. TeamCtx probes configured sources for scoped metadata.
4. TeamCtx renders a short working-context block before the agent starts risky
   work.
5. User or agent can ask `Show why` for any card.
6. User can choose `Use in this session` for optional context.
7. Agent proceeds with context treated as evidence, not hidden instruction.

## Example Terminal Surface

```text
Working context

Needs attention
- Another open PR changed src/auth/token.py 11 minutes ago.
  Why this matters: you are editing the same file.
  Source: GitHub PR #482

Needs attention
- The linked issue changed after this branch started.
  Why this matters: acceptance criteria may have changed.
  Source: Jira API-482

Project guidance
- Token rotation must preserve compatibility for legacy clients.
  Why this matters: this applies to auth-service token changes.
  Source: approved project guidance, originally from Jira API-482
```

If sources are unhealthy:

```text
Working context

Verify before relying
- The release checklist source is stale.
  Why this matters: missing checklist updates should not be treated as no risk.
  Source: Confluence Release Checklist
```

## `Show Why` Example

For the PR collision card:

```text
Show why

This appears because the current task includes src/auth/token.py, and GitHub PR
#482 also changed that file recently.

Source: GitHub PR metadata
Freshness: checked 11 minutes ago
Scope: auth-service, src/auth/token.py
Agent visibility: shown as evidence, not instruction
```

Do not show:

- PR body by default.
- Reviewer names by default.
- Private fork details.
- Any source text classified as blocked.

## `Use In This Session` Example

For an advisory card:

```text
Good to know
- A note in the selected Engineering/Auth folder may be relevant to this auth
  flow.
  Why this matters: it may explain a local token rotation convention.
  Source: Obsidian folder Engineering/Auth
```

Action:

```text
Use in this session
```

Effect:

- The card becomes visible to the agent for this session.
- It does not create project guidance.
- It expires when the session ends.
- It can be hidden for the session.

## Backend Flow

1. `teamctx` receives task/session start.
2. `teamctx` extracts task scope:
   - repo,
   - branch,
   - files mentioned,
   - issue keys,
   - release branch if present.
3. `teamctx-core` probes source fixtures or connectors.
4. `teamctx-core` emits `SourceSignal`s and `SourceStatus` objects.
5. Relevance layer selects scoped signals.
6. Renderer creates `ContextCard`s.
7. `teamctx` prints the terminal working-context block.
8. `Show why` reads explanation fields from the selected signal/card.

## First Data Fixtures

Use these before real connector work:

- local branch start timestamp,
- changed file list,
- open PR/MR touching same file,
- issue update timestamp after branch start,
- stale docs source status,
- optional reviewed guidance record.

## Acceptance Criteria

The slice is successful if:

- The terminal output is useful in under 10 lines for the common case.
- The agent changes behavior in E-014 scenarios 1, 2, and 6.
- `Show why` can explain every visible card without exposing private details.
- `Use in this session` does not create durable guidance.
- Stale/unavailable/blocked source status creates caveats, not instructions.
- The user does not need to know source-signal terminology.

## Engineering Acceptance Criteria

- `teamctx` can render the context block from fixture-backed `teamctx-core` data.
- `teamctx-core` can emit the V1 source-signal shape.
- The renderer maps signal types to sections deterministically.
- A fixture can simulate stale and unavailable sources.
- A fixture can simulate a reviewed guidance record.
- The same fixtures can feed the E-014 benchmark prompts.

## What To Build First

Build fixture-backed behavior before real connectors:

1. Task scope extraction from CLI input and repo state.
2. Fixture source loader.
3. Source-signal normalizer.
4. Context-card renderer.
5. Terminal output.
6. `Show why` lookup.
7. `Use in this session` state.

Only then add one real connector.

## First Real Connector Candidate

GitHub or GitLab metadata, not issue tracker first.

Reason: collision detection around files is easy to explain, easy to scope, and
hard to fake with generic memory language. It proves the product inside the
agent-terminal workflow.

## Product Risk

If the first slice starts with Jira/doc summaries, the product may look like
enterprise search.

If it starts with Git collision and changed-context signals, it feels like a
working-context tool for agents.

## Decision

The first prototype should be fixture-backed and narrow:

- one repo,
- one branch,
- one file,
- one linked issue,
- one collision signal,
- one changed issue signal,
- one reviewed guidance record,
- one stale source caveat,
- `Show why`,
- `Use in this session`.
