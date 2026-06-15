# E-022: Repo Fit Assessment

## Purpose

Compare the fixture-backed prototype plan against the current `teamctx` repo
shape before writing implementation code.

## Product Question

Can the first prototype fit the existing repo cleanly, or does it require a
package restructure first?

## Hypothesis

The product boundary should remain `teamctx` plus durable core, but the first
implementation should keep the core inside the existing package until the split
is earned.

## Inputs

- Existing `pyproject.toml`.
- Existing `src/teamctx` package.
- Existing ADRs.
- E-018 source-signal contract.
- E-019 package boundary.
- E-021 prototype build plan.

## Output

A repo-fit recommendation and implementation adjustment.
