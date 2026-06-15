# E-027: Fixture Prototype Implementation

## Purpose

Implement the fixture-backed prototype described by E-023 and E-024.

## Product Question

Does the first vertical slice still feel coherent when it becomes executable CLI
behavior instead of static docs?

## Hypothesis

A small deterministic implementation can prove the TeamCtx loop without
connectors:

- fixture loads,
- working context renders,
- `Show why` explains a card,
- `Use in this session` adds advisory context without making it guidance,
- benchmark prompt generation reuses the same rendered context.

## Pass Criteria

- Golden output tests pass.
- Default context excludes advisory notes and irrelevant source-health caveats.
- Session use includes the advisory note under `Good to know`.
- Output avoids banned memory/ledger/registry vocabulary.
- Ruff, mypy, and pytest pass.

## Output

An executable prototype in `src/teamctx/` plus tests.
