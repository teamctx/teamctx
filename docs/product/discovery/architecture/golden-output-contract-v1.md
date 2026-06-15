# Golden Output Contract V1

Date: 2026-06-15

Status: discovery draft

## Purpose

Define exact output targets for the fixture-backed prototype.

## Golden Files

| File | Purpose |
| --- | --- |
| `fixtures/vertical-slice/golden/context-default.txt` | Default agent-visible working context. |
| `fixtures/vertical-slice/golden/why-card-pr-collision.txt` | `Show why` output for the GitHub collision card. |
| `fixtures/vertical-slice/golden/context-after-use-advisory-note.txt` | Session context after explicitly using an advisory note card. |
| `fixtures/vertical-slice/golden/benchmark-context-prompt.txt` | E-014-style context benchmark prompt. |
| `fixtures/vertical-slice/golden/context-release-stale-source.txt` | Release-scoped stale source caveat. |

## Output Rules

- Render `Working context` exactly once.
- Group cards by section in deterministic order.
- Do not include advisory note cards in default agent-visible context.
- Do include advisory note cards after explicit session use.
- Do not include source-health caveats unless they are relevant to the task
  scope.
- Never render internal terms in user-facing output.
- Never include raw source bodies.
- Keep `Source:` human-readable and short.

## Deterministic Section Order

Use this order for the first prototype:

1. `Needs attention`
2. `Project guidance`
3. `Verify before relying`
4. `Source unavailable`
5. `Good to know`

Rationale:

- Collision and changed-source risks come first.
- Reviewed guidance comes before caveats and optional context.
- Advisory context comes last because it is not authority.

## Banned User-Facing Terms

The golden outputs must not include:

- memory
- ledger
- registry
- promotion
- quarantine
- source signal
- advisory match
- authority tier
- normalized artifact
- durable core

## Important Product Check

`context-default.txt` intentionally omits the Obsidian advisory card.

`context-after-use-advisory-note.txt` includes it only after explicit session use.

`context-release-stale-source.txt` proves stale source health can still render
when the task is release-scoped.

This is the prototype's clearest trust-boundary test: context can be safe to show
and still not relevant enough to show by default.
