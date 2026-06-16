# E-041: Source Open On Demand Contract

## Purpose

Define the explicit source-body path that follows E-040 status-only routing.
Status should remain compact by default; source bodies should appear only after a
specific open action and a policy check.

## Product Question

When compact source status is not enough, can TeamCtx expose one relevant source
body without turning the agent workspace into a browsable source dump?

## Hypothesis

A policy-gated `Open source` action can show one allowed source body, keep stale
sources caveated, and block unavailable or policy-blocked bodies even if source
text exists in fixture data.

## Scope

- Extend fixtures with optional `source_artifacts`.
- Add a source-open renderer that accepts a card id or source id.
- Add `teamctx open-source` for the fixture-backed prototype.
- Add one allowed source artifact to the vertical-slice GitHub PR fixture.
- Keep source bodies out of default working context and benchmark prompts.

## Pass Criteria

- Opening an allowed source renders exactly that source body.
- Opening a stale source shows the stale caveat before any body decision.
- Sources with `can_include_source_text=false` do not render body text.
- Blocked or unavailable source bodies do not render, even if a fixture includes
  body text.
- Existing context and benchmark behavior stays unchanged.

## Output

- `src/teamctx/source_open.py`
- `teamctx open-source`
- `tests/test_source_open.py`
- `runs/2026-06-16-e041-open-source-on-demand-contract-v1.md`
