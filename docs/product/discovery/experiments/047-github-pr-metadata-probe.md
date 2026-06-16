# E-047: GitHub PR Metadata Probe

Date: 2026-06-16

## Question

Can the first live source-family probe normalize GitHub PR metadata into Core
Contract V0 without widening the product into source search or source-body
ingestion?

## Method

Add a forge-review normalizer and a narrow GitHub PR probe command. The probe
fetches open PR metadata and changed file paths, then emits a Core Contract V0
document. It does not render terminal cards directly.

The command is explicit:

```bash
teamctx github-pr-probe --repo org/app --path src/auth/token.py
```

It reads a token from `GITHUB_TOKEN` by default, or from a named environment
variable via `--token-env`. PR titles are omitted unless `--include-title` is
passed.

## Included Fields

- Repository full name.
- PR number.
- State.
- URL.
- Changed file paths.
- Created and updated timestamps.
- Labels.
- Title only when explicitly allowed.

## Excluded Fields

- PR comments.
- Review comments.
- Review bodies.
- Raw patches.
- Commit bodies.
- Author identity.
- Broad repo search.

## Result

The slice emits overlapping-file `SourceSignal`s, `SourceOpenTarget`s with
`status_only` source-body state, source health, and context cards through Core
Contract V0.

Missing token or failed access returns source status instead of silently treating
GitHub as healthy.

## Decision

Proceed with this as the first live source-family probe foundation. The next
step is to run it against an opted-in real repo with a token, then wire the
result into the terminal vertical slice.
