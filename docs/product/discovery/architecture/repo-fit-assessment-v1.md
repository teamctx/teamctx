# Repo Fit Assessment V1

Date: 2026-06-15

Status: discovery draft

## Current Repo Shape

The repo is intentionally small:

```text
src/teamctx/
  __init__.py
  cli.py

tests/
  test_project_metadata.py
```

The CLI currently exposes:

```text
teamctx status
```

The project already depends on:

- `click`
- `pydantic`

That is enough for a fixture-backed prototype.

## Existing ADR Fit

The existing ADRs are strongly aligned with the pivot.

| Existing decision | Fit with new direction |
| --- | --- |
| Non-agentic deterministic context broker | Keep. The broker should remain deterministic; models consume context, not create broker facts. |
| Artifact-only privacy boundary | Keep. Source signals are derived from approved artifacts and statuses, not people monitoring. |
| Context cards as primary output | Keep. `ContextCard` is the rendered view over signals and guidance. |
| Source integration layer | Keep, but adjust language from connector count to signal quality. |

## Existing Architecture Fit

The current architecture uses this flow:

```text
Connectors -> Normalized artifacts -> Safety + policy -> Artifact graph -> Card rules -> API/CLI
```

The new discovery work uses this flow:

```text
Source probes -> Source signals/status -> Relevance -> Context cards -> Terminal context
```

These do not conflict.

Best interpretation:

- artifacts are provider-normalized inputs,
- relationships explain why artifacts matter,
- source signals are task-scoped conclusions or caveats,
- context cards are the rendered output.

Do not delete the artifact model. Add source signals as the bridge between
normalized source facts and user-facing cards.

## Package Boundary Adjustment

E-019 recommends two implementation layers:

- `teamctx`, public product surface,
- `teamctx-core`, durable core.

Repo-fit adjustment:

Do not create a separately installable `teamctx-core` package for the first
prototype.

Use this structure first:

```text
src/teamctx/
  cli.py
  context.py
  render.py
  why.py
  session.py
  core/
    __init__.py
    signals.py
    guidance.py
    fixtures.py
    policy.py
```

Reason:

- The repo has one package today.
- A physical package split would add packaging work before product proof.
- The architectural boundary can exist inside the package.
- Extraction is easy later if the boundary proves valuable.

## Prototype Fit

The E-021 commands fit the existing Click CLI:

```text
teamctx context --fixture ...
teamctx why card_pr_collision --fixture ...
teamctx use card_auth_notes_advisory --session demo --fixture ...
teamctx benchmark-prompt --scenario auth-token-retry --variant context --fixture ...
```

No new dependencies are needed for the prototype.

`pydantic` can validate fixture models.

`click` can host commands.

`pytest` can verify golden outputs.

## Minimal Implementation Plan

When coding starts, prefer this sequence:

1. Add pydantic models for signals, guidance, and cards.
2. Add fixture loader.
3. Add deterministic renderer.
4. Add `teamctx context --fixture`.
5. Add `teamctx why`.
6. Add session-only selection file for `teamctx use`.
7. Add benchmark prompt generation.
8. Add golden tests.

## Test Fit

Current tests are metadata/boundary tests only.

New tests should be narrow golden tests:

- fixture loads and validates,
- default render excludes advisory note from agent-visible output,
- stale source renders under `Verify before relying`,
- project guidance comes from guidance record,
- `why` output is source-backed and does not reveal hidden source text,
- `use` changes session state only,
- benchmark prompt matches E-014 style.

## Product Language Fit

Existing repo text says:

```text
git status, but for team context
```

That still works.

The discovery phrase is more specific:

```text
working context at agent-terminal start and resume points
```

Recommendation:

Keep both for now:

- public tagline: `git status, but for team context`,
- product mechanism: `Working context` shown at start/resume.

## Main Risk

The old architecture says `Normalized artifacts` and `Artifact graph`.

The new product docs say `SourceSignal`.

If both concepts remain vague, the model will sprawl.

Recommended discipline:

- provider output normalizes to artifacts,
- artifacts plus relationships produce source signals,
- source signals plus guidance records render context cards.

## Decision

Prototype inside the existing `teamctx` package.

Preserve the future `teamctx-core` boundary as an internal module boundary, not a
separate package yet.

Do not restructure packaging until the fixture-backed prototype proves the loop.
