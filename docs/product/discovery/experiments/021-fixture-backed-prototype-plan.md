# E-021: Fixture-Backed Prototype Plan

## Purpose

Turn the first vertical slice into a concrete prototype plan without starting
real connector work.

## Product Question

What should we build first to validate the TeamCtx loop end to end?

## Hypothesis

A fixture-backed CLI prototype can validate the product loop faster and more
honestly than a connector-first build.

The prototype should prove:

- scope extraction,
- source-signal rendering,
- `Show why`,
- `Use in this session`,
- source-health caveats,
- and benchmark prompt generation.

## Method

Create:

- a prototype build plan,
- concrete prototype command names,
- and a JSON fixture that represents one realistic task.

## Output

A buildable prototype plan and a demo fixture for the auth token retry scenario.
