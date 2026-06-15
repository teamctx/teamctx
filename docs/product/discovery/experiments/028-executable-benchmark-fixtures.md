# E-028: Executable Benchmark Fixtures

## Purpose

Turn the six primary E-014 benchmark scenarios into executable fixtures.

## Product Question

Can the benchmark pack be generated from the same deterministic fixture path as
the prototype, instead of hand-maintained prompt text?

## Hypothesis

Each benchmark scenario can be represented as a small fixture with:

- task,
- scope,
- source signals or guidance records,
- expected context cards.

The CLI can generate baseline and context prompts from these fixtures without
scenario-specific code.

## Output

Six primary benchmark fixtures and tests proving prompt generation works.
