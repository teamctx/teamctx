# E-019: Package Boundary

## Purpose

Decide how to combine the TeamCtx product surface with the durable/backend work
formerly explored through Ambara.

## Product Question

Should this become two complementary packages, and if so what are they?

## Hypothesis

There should be one product and two implementation layers:

- TeamCtx: the user-facing product surface for agent-terminal working context.
- TeamCtx Core: the durable source-signal and guidance engine.

The durable core should not be a standalone product users are expected to want or
understand by itself.

## What This Tests

- Does the split make engineering cleaner without splitting the product story?
- Can the durable layer exist without bringing back memory/ledger/registry
  language?
- Does TeamCtx remain the thing users experience?
- Can the old Ambara work survive as implementation DNA rather than product
  identity?

## Output

A recommended package boundary and naming stance.
