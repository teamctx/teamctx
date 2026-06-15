# E-025 Run: Relevance Noise Boundary V1

Date: 2026-06-15

Purpose: reduce default prototype noise by scoping stale source-health caveats.

## Created Artifact

- `architecture/relevance-noise-boundary-v1.md`

## Updated Artifacts

- `fixtures/vertical-slice/auth-token-retry-v1.json`
- `fixtures/vertical-slice/golden/context-default.txt`
- `fixtures/vertical-slice/golden/context-after-use-advisory-note.txt`
- `fixtures/vertical-slice/golden/benchmark-context-prompt.txt`
- `fixtures/vertical-slice/golden/context-release-stale-source.txt`

## Decision

The stale release checklist is not default context for the auth-token edit.

It remains a valid caveat for release-scoped tasks.

## Product Interpretation

Source health matters, but only when source health changes confidence for the
current work.

This keeps TeamCtx from becoming noisy while preserving the fail-closed stance
for stale or unavailable sources.
