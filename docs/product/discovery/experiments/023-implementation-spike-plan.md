# E-023: Implementation Spike Plan

## Purpose

Define the smallest implementation spike that would prove the fixture-backed
TeamCtx loop without starting connector work.

## Product Question

What exactly should we build first if we decide to move from discovery docs into
code?

## Hypothesis

The first spike should implement a deterministic fixture loop inside the existing
`teamctx` package:

- load one fixture,
- render working context,
- explain a card with `Show why`,
- make an advisory card session-visible with `Use in this session`,
- and generate an E-014-style benchmark prompt.

## Constraint

No real connectors. No package split. No dashboard. No memory language.

## Output

A build-ready spike plan with module boundaries, tests, and stop conditions.
