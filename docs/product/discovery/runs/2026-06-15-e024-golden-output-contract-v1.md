# E-024 Run: Golden Output Contract V1

Date: 2026-06-15

Purpose: create exact golden outputs for the fixture-backed prototype.

## Created Artifacts

- `architecture/golden-output-contract-v1.md`
- `fixtures/vertical-slice/golden/context-default.txt`
- `fixtures/vertical-slice/golden/why-card-pr-collision.txt`
- `fixtures/vertical-slice/golden/context-after-use-advisory-note.txt`
- `fixtures/vertical-slice/golden/benchmark-context-prompt.txt`

## Product Decision Locked Into The Goldens

Default working context excludes advisory local-note matches.

Explicit `Use in this session` includes the advisory card in session context, but
still does not make it `Project guidance`.

## Why This Matters

The golden files make product drift visible during implementation. If a future
prototype output starts explaining internals, sounding like memory, or treating
notes as policy, the tests should catch it.
