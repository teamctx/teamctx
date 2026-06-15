# Prototype Implementation Spike V1

Date: 2026-06-15

Status: discovery draft

## Goal

Build the smallest fixture-backed CLI prototype that proves the TeamCtx working
context loop.

## Non-Negotiables

- Deterministic: no LLM in the broker.
- Fixture-backed: no live connector work.
- One installable package: no physical `teamctx-core` package yet.
- User-facing language must not include memory, ledger, registry, promotion,
  quarantine, source signal, advisory match, or authority tier.
- Advisory note cards are not agent-visible by default.

## Proposed Files

```text
src/teamctx/
  cli.py                 # add prototype commands to existing click group
  context.py             # high-level orchestration for rendering context
  render.py              # text rendering for context cards and benchmark prompts
  why.py                 # explanation text for cards
  session.py             # session-only card selections
  core/
    __init__.py
    models.py            # pydantic models for fixture, signals, guidance, cards
    fixtures.py          # fixture loading and validation
    cards.py             # deterministic card construction from fixture data
    policy.py            # agent visibility and section rules

tests/
  test_fixture_prototype.py
```

## Prototype Commands

These command names are still provisional.

```text
teamctx context --fixture docs/product/discovery/fixtures/vertical-slice/auth-token-retry-v1.json
teamctx why card_pr_collision --fixture docs/product/discovery/fixtures/vertical-slice/auth-token-retry-v1.json
teamctx use card_auth_notes_advisory --session demo --fixture docs/product/discovery/fixtures/vertical-slice/auth-token-retry-v1.json
teamctx benchmark-prompt --scenario auth-token-retry --variant context --fixture docs/product/discovery/fixtures/vertical-slice/auth-token-retry-v1.json
```

## Implementation Sequence

### Step 1: Models

Add pydantic models for:

- `Fixture`
- `SourceSignal`
- `GuidanceRecord`
- `ContextCard`
- `SessionSelection`

Acceptance:

- The auth-token fixture validates.
- Unknown top-level fields are rejected or explicitly ignored by policy.
- Required trust fields exist: `signal_type`, `source_family`, `freshness`,
  `visibility`, and `policy`.

### Step 2: Fixture Loader

Add a loader that reads a fixture path and returns a validated fixture.

Acceptance:

- Missing fixture path produces a clear CLI error.
- Invalid JSON produces a clear CLI error.
- Valid fixture preserves card order from `expected_cards` for the prototype.

### Step 3: Card Policy

Add deterministic rules:

- include visible source signals when `policy.can_render_to_agent` is true,
- include active guidance records,
- exclude advisory cards from default agent-visible output when
  `default_agent_visible` is false,
- render stale sources as caveats, not guidance,
- render source-health caveats only when relevant to the current task scope.

Acceptance:

- `card_auth_notes_advisory` is absent from default `teamctx context` output.
- `card_stale_docs` is absent from the auth-token default output because the task
  is not release-scoped.
- `card_stale_docs` renders under `Verify before relying` for a release-scoped
  context.
- `card_project_guidance` comes from a guidance record.

### Step 4: Renderer

Render cards to terminal text exactly like the golden file.

Acceptance:

- Output matches `fixtures/vertical-slice/golden/context-default.txt`.
- No hidden source text appears.
- No internal terms appear.

### Step 5: Show Why

Render explanation for a card from refs and source metadata.

Acceptance:

- `teamctx why card_pr_collision` matches
  `fixtures/vertical-slice/golden/why-card-pr-collision.txt`.
- Explanation says agent visibility is evidence, not instruction.
- Explanation does not include PR body, reviewer names, or private details.

### Step 6: Use In This Session

Store session-only selected card ids.

Suggested prototype storage:

```text
/tmp/teamctx-sessions/{session}.json
```

Acceptance:

- `teamctx use card_auth_notes_advisory --session demo` records only session
  state.
- Fixture JSON is not modified.
- A session-aware context render can include the advisory card.
- The advisory card still does not become `Project guidance`.

### Step 7: Benchmark Prompt

Generate an E-014-style context prompt from visible cards.

Acceptance:

- Output matches `fixtures/vertical-slice/golden/benchmark-context-prompt.txt`.
- Advisory note is omitted unless selected for the session.
- Prompt includes evidence-only instruction.

## Golden Tests

Create tests for:

- fixture validation,
- default context render,
- `Show why`,
- session use,
- benchmark prompt,
- banned user-facing language.

Banned user-facing language in prototype outputs:

- memory,
- ledger,
- registry,
- promotion,
- quarantine,
- source signal,
- advisory match,
- authority tier.

## Stop Conditions

Stop the spike and return to product design if:

- The common-case default context output needs more than 12 nonblank lines to
  be useful.
- Advisory context cannot be cleanly separated from agent-visible context.
- `Show why` requires exposing source bodies.
- Session state feels like hidden durable memory.
- The implementation needs real connectors to make the fixture loop meaningful.

## Success Criteria

The spike succeeds if one fixture can drive:

- a useful terminal context block,
- a safe explanation,
- a session-only advisory card action,
- and a benchmark prompt.

If that works, the next coding step is one real Git hosting metadata connector.
