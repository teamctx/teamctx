# E-008 Run: Action Language Comparison V1

Date: 2026-06-15

Purpose: compare labels for temporary agent-visible context.

## Base Card

```text
Needs attention
The linked Jira issue changed after this branch started.

Why this matters: acceptance criteria may have changed.
Source: Jira API-482

Actions: [candidate] | Draft guidance | Hide for this session
```

The intended action contract:

- The item becomes available to the agent in the current session.
- The item remains source-backed context, not approved guidance.
- The item expires when the session ends.
- No future guidance, source setting, or source artifact is changed.

## Candidate: Use In This Session

```text
Actions: Use in this session | Draft guidance | Hide for this session
```

Likely interpretation:

- Strong: says the scope is this session.
- Strong: implies the item will be used now, not saved later.
- Weak: may still be vague about whether the agent sees it or only the human
  should consider it.

Expected confirmation text:

```text
Using in this session
This context is now available to the agent until the session ends.

Actions: Stop using | Show why
```

Verdict: strongest current candidate.

## Candidate: Pin For This Session

```text
Actions: Pin for this session | Draft guidance | Hide for this session
```

Likely interpretation:

- Strong: suggests visible, undoable, temporary state.
- Strong: common enough in software UI.
- Weak: may sound like managing a board or sidebar, not terminal flow.
- Weak: does not by itself say the agent sees the pinned item.

Expected confirmation text:

```text
Pinned for this session
This context is now available to the agent until the session ends.

Actions: Unpin | Show why
```

Verdict: viable, but more UI-ish.

## Candidate: Add To This Session

```text
Actions: Add to this session | Draft guidance | Hide for this session
```

Likely interpretation:

- Strong: implies the session receives something.
- Weak: "add" is vague; add where?
- Weak: may sound like it appends a note rather than gives context to the agent.

Expected confirmation text:

```text
Added to this session
This context is now available to the agent until the session ends.

Actions: Remove | Show why
```

Verdict: acceptable but less direct than `Use in this session`.

## Candidate: Show To Agent

```text
Actions: Show to agent | Draft guidance | Hide for this session
```

Likely interpretation:

- Strong: extremely clear that the agent sees it.
- Weak: awkward if the user is also reading the terminal output.
- Weak: too implementation-revealing; product should not feel like manually
  feeding scraps to an agent.

Expected confirmation text:

```text
Shown to agent
This context is available for the current session only.

Actions: Stop showing | Show why
```

Verdict: clear but too mechanical as a primary label. Useful in explanations.

## Candidate: Keep Visible

```text
Actions: Keep visible | Draft guidance | Hide for this session
```

Likely interpretation:

- Strong: pairs with hide.
- Weak: sounds human-visible only, not agent-visible.
- Weak: does not communicate session expiry.

Verdict: reject for this job.

## Comparison Table

| Label | Agent sees it? | Session-only? | Feels terminal-native? | Risk |
| --- | --- | --- | --- | --- |
| `Use in this session` | medium-high | high | high | needs confirmation text |
| `Pin for this session` | medium | high | medium | UI metaphor |
| `Add to this session` | medium | high | medium | add where? |
| `Show to agent` | high | medium | medium | too mechanical |
| `Keep visible` | low | low | medium | human-visible only |

## Finding

Use `Use in this session` as the leading label, with confirmation text that
makes the agent effect explicit:

```text
This context is now available to the agent until the session ends.
```

Keep `Pin for this session` as a fallback if CPO/user feedback prefers a visible
state metaphor.

## Updated Action Set Candidate

- `Open source`
- `Use in this session`
- `Hide for this session`
- `Draft guidance`
- `Show why`
- `Suggest update`
- `Continue without it`

## Decision

Provisional: prefer `Use in this session` over `Pin for this session`, pending
CPO review.
