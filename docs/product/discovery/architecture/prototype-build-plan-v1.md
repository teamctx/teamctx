# Prototype Build Plan V1

Date: 2026-06-15

Status: discovery draft

## Goal

Build a fixture-backed CLI prototype that proves the TeamCtx working-context loop
before real connector work.

## Prototype Scope

Use one fixture:

- `fixtures/vertical-slice/auth-token-retry-v1.json`

Support one task:

```text
Update src/auth/token.py to add token rotation retry handling for API-482.
```

## Prototype Commands

These are prototype command names, not final product commitments.

### Render Working Context

```text
teamctx context --fixture fixtures/vertical-slice/auth-token-retry-v1.json
```

Expected output:

```text
Working context

Needs attention
- Another open PR changed src/auth/token.py 11 minutes ago.
  Why this matters: you are editing the same file.
  Source: GitHub PR #482

Needs attention
- The linked issue changed after this branch started.
  Why this matters: acceptance criteria may have changed.
  Source: Jira API-482

Project guidance
- Token rotation must preserve compatibility for legacy clients.
  Why this matters: this applies to auth-service token changes.
  Source: approved project guidance, originally from Jira API-482

Verify before relying
- The release checklist source is stale.
  Why this matters: missing checklist updates should not be treated as no risk.
  Source: Confluence Release Checklist
```

The advisory note card should not be agent-visible by default. It can appear in a
user-visible context list or behind an option, then be added with `Use in this
session`.

### Show Why

```text
teamctx why card_pr_collision --fixture fixtures/vertical-slice/auth-token-retry-v1.json
```

Expected output:

```text
Show why

This appears because the current task includes src/auth/token.py, and GitHub PR
#482 also changed that file recently.

Source: GitHub PR metadata
Freshness: fresh
Scope: auth-service, src/auth/token.py
Agent visibility: shown as evidence, not instruction
```

### Use In This Session

```text
teamctx use card_auth_notes_advisory --session demo --fixture fixtures/vertical-slice/auth-token-retry-v1.json
```

Expected behavior:

- Creates a session-only selection.
- Makes the advisory card agent-visible for the `demo` session.
- Does not create project guidance.
- Does not modify the fixture.

### Generate Benchmark Prompt

```text
teamctx benchmark-prompt --scenario auth-token-retry --variant context --fixture fixtures/vertical-slice/auth-token-retry-v1.json
```

Expected behavior:

- Emits an E-014-style prompt using rendered cards.
- Does not include hidden source text.
- Does not include advisory note unless selected for the session.

## Implementation Sequence

1. Load fixture JSON.
2. Validate minimum shape.
3. Map source signals and guidance records to context cards.
4. Render terminal context block.
5. Implement `why` by looking up card refs.
6. Implement session-use state in a local temp/session file.
7. Add benchmark prompt generation.
8. Add golden-output tests.

## Minimal Modules

Possible module split inside the prototype:

```text
teamctx/
  cli.py
  context.py
  render.py
  why.py
  session.py
teamctx_core/
  signals.py
  guidance.py
  fixtures.py
  policy.py
```

This mirrors the package boundary without forcing final packaging yet.

## Golden Tests

Create golden tests for:

- context render order,
- no advisory note in default agent-visible output,
- `why` output does not reveal private details,
- stale source renders as caveat, not guidance,
- `use` creates session selection only,
- benchmark prompt omits hidden source text.

## Prototype Pass Criteria

The prototype passes if:

- The fixture renders the expected working-context block.
- `Show why` works for every visible card.
- `Use in this session` changes only session state.
- Benchmark prompt generation can reproduce E-014 scenario shape.
- The implementation never uses memory, ledger, registry, or promotion language
  in user-facing output.

## Decisions Deferred

- Real connector APIs.
- OAuth or credential handling.
- Persistent storage format.
- Final CLI command names.
- Dashboard or settings UI.
- Cloud sync.

## Engineering Bias

Keep the first prototype boring.

If it cannot prove value with a single JSON fixture, adding connectors will only
make the product harder to reason about.
