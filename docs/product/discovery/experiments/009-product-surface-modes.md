# E-009 Product Surface Modes

## Question

What should TeamCtx show automatically in the agent terminal, what should be
available on request, and what should live in source settings or diagnostics?

## Hypothesis

The product needs three surfaces:

1. Working context: small, automatic, task-changing context.
2. Explain/context details: on-demand trust and source explanation.
3. Source settings/health: admin or diagnostic source status.

Mixing these surfaces will make the product feel noisy, creepy, or too much like
enterprise search.

## Method

Classify tested card types into surfaces. For each type, decide:

- show automatically
- show only when asked
- show only in settings/diagnostics
- never show

## Pass Criteria

- Normal working context stays short.
- Private/blocked/inaccessible details do not leak.
- Users can still understand why context appeared.
- Source-health gaps are visible when they affect confidence.
- Admin setup does not pollute everyday flow.

## Fail Criteria

- Normal context becomes a source audit log.
- Users cannot find why something appeared.
- Source settings are required for everyday use.
- Hidden/private omissions are revealed through normal cards.

## Decision

Pending.
