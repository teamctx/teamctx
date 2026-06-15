# E-007 Action Semantics

## Question

What does each user action actually do to the human terminal surface, the agent's
working context, and any future guidance workflow?

## Hypothesis

TeamCtx actions should be few, literal, and consequence-clear. A user should be
able to predict whether an action affects:

- this visible terminal session
- what the agent receives now
- future sessions
- source settings
- reviewed guidance

## Actions Under Test

- `Open source`
- `Pin for this session`
- `Hide for this session`
- `Draft guidance`
- `Show why`
- `Suggest update`
- `Continue without it`
- `Review source settings`

## Method

For each action, define:

1. User intent.
2. Immediate UI result.
3. Agent-visible result.
4. Persistence behavior.
5. Failure mode.
6. Better label if unclear.

## Pass Criteria

- Each action has one obvious meaning.
- Session-only actions cannot accidentally create future guidance.
- Future actions cannot become active without an explicit draft/review/accept
  step.
- Agent-visible context is clear and inspectable.
- Admin/source-setting actions are not confused with everyday actions.

## Fail Criteria

- Any action means different things in different cards.
- Users cannot tell whether the agent sees the item.
- Hiding mutates source settings by accident.
- Drafting guidance sounds like automatic memory.
- Source-setting controls leak into everyday flow too often.

## Decision

Pending.
