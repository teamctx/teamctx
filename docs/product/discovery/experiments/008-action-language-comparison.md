# E-008 Action Language Comparison

## Question

Which user-facing action label best communicates temporary agent-visible context
without implying future memory, source mutation, or UI state management?

## Candidate Labels

- `Use in this session`
- `Pin for this session`
- `Add to this session`
- `Show to agent`
- `Keep visible`

## Hypothesis

`Use in this session` may be clearer than `Pin for this session` in a terminal
product because it names the consequence instead of the UI metaphor. However,
`Pin` may still be useful if users need a visible state they can undo.

## Method

Use the same source card with different action labels. For each label, ask:

1. What happens if you choose it?
2. Does the agent see the context?
3. Does it persist after the session?
4. Does it change future guidance or source settings?
5. Does it sound like memory, tracking, or UI clutter?

## Pass Criteria

- Users correctly expect the agent sees the item in this session.
- Users correctly expect it expires after the session.
- Users do not expect future guidance or source settings to change.
- The label sounds natural in an agent terminal.

## Fail Criteria

- Users think the action saves something for the future.
- Users think it opens the source rather than adding context to the session.
- Users think it changes source settings.
- Users cannot tell whether the agent receives the context.

## Decision

Pending.
