# E-004 Future Context Loop

## Question

When something important appears in a source, how does it become useful in a
future session without feeling like surveillance, hidden memory, or a new
knowledge base to manage?

## Hypothesis

The user-facing loop should be:

1. A source-backed item appears during current work.
2. The user chooses a temporary or future action.
3. Temporary action pins the item only for this session.
4. Future action opens an editable draft, scoped to a repo/project/task.
5. A reviewed draft becomes saved guidance.
6. Saved guidance appears later only when the scope matches.
7. The user can see why it appeared and suggest an update.

The product should not silently save source text for the future.

## Language Under Test

Temporary context candidates:

- `Pin for this session`
- `Show in this session`
- `Use for this task`

Future context candidates:

- `Draft guidance`
- `Save as project guidance`
- `Add to project notes`
- `Keep for future`

Current leaning: `Pin for this session` and `Draft guidance` are clearer than
`Use now` and `Save for later`.

## Method

For each candidate source item:

1. Show the original card.
2. Show the action chosen.
3. Show the draft or pinned-session result.
4. Show how it appears in a later session.
5. Ask whether the loop feels useful, too permanent, too vague, or too much like
   memory.

## Pass Criteria

- The user can predict what happens after each action.
- Future guidance is editable before it is saved.
- Scope is visible before anything becomes future guidance.
- Later resurfacing explains why it appeared.
- Nothing implies the product saves everything automatically.

## Fail Criteria

- The user thinks TeamCtx is remembering them personally.
- `Draft guidance` or its replacement feels like tracking.
- The future item appears too broadly.
- The source text becomes treated as authority without review.
- The user cannot distinguish temporary session context from future guidance.

## Decision

Pending.
