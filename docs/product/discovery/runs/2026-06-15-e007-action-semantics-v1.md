# E-007 Run: Action Semantics V1

Date: 2026-06-15

Purpose: define the product contract for the action labels that survived E-002
through E-006.

## Action: Open Source

User intent: I want to inspect the original artifact myself.

Immediate UI result:

```text
Opening source: GitHub PR #482
```

Agent-visible result:

- No new authority is created.
- If the user asks the agent to inspect the opened source, that is a separate
  action/tool path.

Persistence:

- None.

Failure mode:

- If the source cannot open, explain access or availability without dumping raw
  errors.

Verdict: keep. Clear and concrete.

## Action: Pin For This Session

User intent: Make this item available to the agent while we work right now.

Immediate UI result:

```text
Pinned for this session
This context is now available to the agent for the current session only.

Actions: Unpin | Show why
```

Agent-visible result:

- The pinned item enters the session context packet.
- It is labeled as source-backed context, not reviewed guidance.
- It includes source, reason, freshness, and any verify-before-relying state.

Persistence:

- Expires when the session ends.
- Does not create future guidance.
- Does not change source settings.

Failure mode:

- If users expect pinning to persist, the label may need to become `Use in this
  session`.

Verdict: keep testing. Candidate alternative: `Use in this session`.

## Action: Hide For This Session

User intent: This may be valid, but I do not want it in the current flow.

Immediate UI result:

```text
Hidden for this session
This does not change the source or future guidance.

Actions: Undo
```

Agent-visible result:

- The hidden item is removed from the visible/prompted session context.
- The agent should not rely on it unless the user later restores it.

Persistence:

- Session-only.
- Does not mute the source.
- Does not delete saved guidance.

Failure mode:

- Users may expect future suppression. Offer separate source/settings path only
  after repeated hides.

Verdict: keep. Better than `Ignore`.

## Action: Draft Guidance

User intent: This may matter in future sessions; help me turn it into scoped
project guidance.

Immediate UI result:

```text
Draft project guidance

Suggested guidance:
Token rotation must preserve compatibility for legacy clients.

Applies to: auth-service
Source: Jira API-482
Future use: inactive until accepted

Actions: Save draft | Edit | Cancel
```

Agent-visible result:

- No future guidance is active yet.
- Current session may still use the original source item if pinned or visible.

Persistence:

- Creates an inactive draft.
- Draft has source, scope, author/action metadata, and review/acceptance state.
- It appears in future sessions only after acceptance/review.

Failure mode:

- `Guidance` may feel too formal.
- `Save draft` may feel like document work.
- Review path may be too heavy.

Verdict: keep testing. Candidate alternatives: `Draft project note`, `Save as
project note`, `Add project guidance`.

## Action: Show Why

User intent: Explain why this appeared without opening the original source.

Immediate UI result:

```text
Why this appeared
- Scope matched: auth-service
- Source matched: Jira API-482
- Freshness: updated today
- Status: approved project guidance
```

Agent-visible result:

- None by default; this is an explanation to the user.

Persistence:

- None.

Failure mode:

- Explanation could expose implementation language. Keep it source/scope/freshness
  oriented.

Verdict: keep. Strong trust control.

## Action: Suggest Update

User intent: This saved guidance seems wrong, stale, or incomplete.

Immediate UI result:

```text
Suggest an update

Current guidance:
Token rotation must preserve compatibility for legacy clients.

What should change?
```

Agent-visible result:

- None until the user submits an update or draft.

Persistence:

- Creates an update draft, not an immediate mutation.

Failure mode:

- If the review path is too slow, stale guidance will accumulate.

Verdict: keep for saved guidance only.

## Action: Continue Without It

User intent: I understand this source is stale/unavailable/access-limited, and I
want to keep working.

Immediate UI result:

```text
Continuing without Jira context
Issue-related context may be incomplete in this session.

Actions: Retry source | Show source status
```

Agent-visible result:

- The agent receives an explicit caveat that the source is unavailable/stale.
- No synthetic issue context is created.

Persistence:

- Session-only.
- Does not disable the source.

Failure mode:

- Too many source warnings could train users to click through.

Verdict: keep for stale/unavailable source cards.

## Action: Review Source Settings

User intent: I want to change or inspect which sources are included.

Immediate UI result:

- Open settings, config docs, or CLI setup path.

Agent-visible result:

- None unless settings change and sources refresh.

Persistence:

- May change source configuration if the user edits settings.

Failure mode:

- Too admin-like for normal working context.

Verdict: keep out of normal cards except source-health/admin contexts.

## Findings

Action groups:

- Session actions: `Pin for this session`, `Hide for this session`, `Continue
  without it`.
- Source actions: `Open source`, `Review source settings`.
- Trust actions: `Show why`.
- Future actions: `Draft guidance`, `Suggest update`.

Product rules:

1. Every action must declare whether the agent sees the result.
2. Session actions expire by default.
3. Future actions create drafts, not active guidance.
4. Settings actions should not appear in ordinary cards unless the issue is a
   source-health problem.
5. `Use now` remains rejected because it hides too many consequences.

Open naming question:

`Pin for this session` is accurate but maybe UI-ish. `Use in this session` may
be clearer in a terminal. Test both.

## Decision

Revise action model: proceed with `Open source`, `Use in this session` or `Pin
for this session`, `Hide for this session`, `Draft guidance`, `Show why`,
`Suggest update`, and `Continue without it`. Keep `Review source settings` out
of ordinary flow.
