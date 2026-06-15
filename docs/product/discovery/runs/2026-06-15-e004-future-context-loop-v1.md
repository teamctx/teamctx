# E-004 Run: Future Context Loop V1

Date: 2026-06-15

Purpose: test the user-facing loop from a source-backed moment to future saved
guidance, without using the internal word `promotion`.

## Scenario

The user is editing `auth-service` token rotation code. A linked Jira issue was
updated after the branch started.

## Step 1: Initial Card

```text
Needs attention
The linked Jira issue added a compatibility requirement today.

Why this matters: your branch started before the issue changed.
Source: Jira API-482

Actions: Pin for this session | Draft guidance | Ignore
```

## Step 2A: Temporary Action

User chooses: `Pin for this session`

```text
Pinned for this session
Token rotation must preserve legacy client compatibility.

The agent can use this while working in the current session. It will not be
saved for future sessions.
Source: Jira API-482

Actions: Unpin | Open source
```

Expected user understanding:

- This affects the current agent session.
- It does not become team guidance.
- It should disappear when the session ends unless another source surfaces it.

Risk:

- `Pin` may sound like a UI object instead of terminal behavior.
- The product must be clear whether the agent sees pinned context immediately.

## Step 2B: Future Action

User chooses: `Draft guidance`

```text
Draft project guidance

Suggested guidance:
Token rotation must preserve compatibility for legacy clients.

Applies to: auth-service
Source: Jira API-482
Review: required before future sessions use it

Actions: Save draft | Edit | Cancel
```

Expected user understanding:

- Nothing is silently saved.
- The sentence is editable.
- Scope is visible.
- Review is required before it appears later.

Risk:

- `Save draft` may still sound like a document-management task.
- `Review required` is correct but may feel heavy for small teams.

## Step 3: Saved Draft State

After user saves draft:

```text
Draft saved
This guidance will not appear in future sessions until reviewed.

Actions: Open draft | Dismiss
```

Expected user understanding:

- The draft exists, but is not active future context.
- This is not memory yet, and not authoritative.

Risk:

- Users may expect saved draft to work immediately.
- The review path needs to be light enough that the value is not lost.

## Step 4: Later Session After Review

A later agent session starts in `auth-service`.

```text
Saved for this project
Token rotation must preserve compatibility for legacy clients.

Why this matters: this applies to auth-service token changes.
Source: approved project guidance, originally from Jira API-482

Actions: Show why | Suggest update | Hide for this session
```

Expected user understanding:

- This guidance applies because of repo/task scope.
- It was approved, not automatically remembered.
- The user can challenge or hide it.

Risk:

- `Saved for this project` may still sound like permanent storage.
- `Approved project guidance` may be too formal.

## Step 5: Later Session Outside Scope

A later agent session starts in `billing-service`.

```text
Working context
No saved project guidance matched this task.
```

Expected user understanding:

- The auth guidance did not appear because scope did not match.
- TeamCtx is not dumping all saved knowledge.

Risk:

- This empty-state line may be unnecessary noise.

## Findings

Strong candidates:

- `Pin for this session` is clearer than `Use now`.
- `Draft guidance` is clearer than `Save for later` because it implies review
  and editing.
- `Hide for this session` is clearer than `Ignore` for context that might be
  valid but unwanted right now.

Weak candidates:

- `Saved for this project` may feel too storage-like.
- `Review required` may feel enterprise-heavy unless the review path is almost
  invisible for solo/small-team use.
- `No saved project guidance matched this task` may be unnecessary unless the
  user asked why there was no context.

Product decision candidate:

Use three distinct actions:

- `Pin for this session`: temporary, agent-visible now, expires with session.
- `Draft guidance`: editable future candidate, scoped, inactive until reviewed.
- `Hide for this session`: suppress valid context without changing the source.

Do not use `Use now` as a primary action until it has a concrete behavior.

## CPO Review Questions

1. Does `Draft guidance` feel like the right replacement for internal
   `promotion`?
2. Does `Pin for this session` make sense in an agent terminal?
3. Is `Saved for this project` too permanent or too document-like?
4. Should review be explicit in the UI, or implied by the draft workflow?
5. Should an out-of-scope later session say nothing, or say no guidance matched?

## Decision

Pending CPO review.
