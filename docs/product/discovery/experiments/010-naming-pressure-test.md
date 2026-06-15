# E-010 Naming Pressure Test

## Question

Which labels make the product legible without teaching users TeamCtx concepts?

## Names Under Test

Container label:

- `Working context`
- `Context for this task`
- `What matters now`
- `Before you continue`

Temporary action:

- `Use in this session`
- `Pin for this session`
- `Show to agent`

Future action:

- `Draft guidance`
- `Draft project guidance`
- `Save as project note`
- `Add project guidance`

Saved section:

- `Saved for this project`
- `Project guidance`
- `Applies to this project`
- `Already agreed`

## Method

For each label, score:

1. Does it describe user value rather than implementation?
2. Can the user predict what happens?
3. Does it avoid memory/tracking/storage vibes?
4. Does it fit a terminal experience?
5. Does it avoid enterprise/process heaviness?

## Pass Criteria

- Label works without a glossary.
- Label predicts behavior correctly.
- Label does not imply broad storage, monitoring, or hidden memory.
- Label can survive repeated use without sounding cute or patronizing.

## Fail Criteria

- Label needs docs to explain it.
- Label sounds like tracking or compliance.
- Label hides whether the agent sees context.
- Label suggests persistence when behavior is session-only.

## Decision

Pending.
