# GitHub truncation honesty (no false clear on busy repos)

**Status:** design, CTO call (driving) · **Date:** 2026-06-28

## Problem

`connectors/github.py` fetches only the first page of open PRs (`pulls?state=open&per_page=30`, no
pagination) and the first 100 files per PR (`files?per_page=100`). On a busy repo, a colliding PR
past the first page (or a colliding file past the first 100 in a PR) is never seen, and the conflict
check renders as a clean "no open PRs touch your files." That is a **false clear at the source** of
the very signal teamctx exists to make trustworthy.

## Decision

Truncation becomes an honest UNKNOWN, not a clear. We reuse the machinery that already exists: a
source status that is not `fresh` maps (via `assess_completeness`, select.py) to
`incomplete[stale-dep]`, which makes the conflict verdict UNKNOWN when no refuting collision card is
present. A **visible** collision still fires (the cards are built from the PRs we did see, regardless
of truncation). So:

- truncated, a visible collision in the page we fetched -> the collision card -> conflict = found.
- truncated, no visible collision -> non-fresh status -> `incomplete[stale-dep]` -> conflict = UNKNOWN.
- not truncated, no collision -> `fresh` -> conflict = clear (as today).

This kills the false clear with **no change to the theorem-backed core closure, the assessment, or
the render**. Two files change.

## Design

### `connectors/github.py`
- Raise the PR list to `per_page=100` (one page covers most repos completely).
- `fetch_github_pull_requests` returns the PRs **and** a `truncated: bool` (a small frozen dataclass
  `ForgeReviewFetch(prs, truncated)` or a tuple). `truncated` is True if the PR list came back full
  (`len(pulls_payload) >= 100`, a full page implies more we did not fetch) OR any fetched PR's file
  list came back full (`len(files) >= 100`, that PR's changed paths are incomplete).
- We do **not** paginate further. Bounding to one page keeps the per-edit hook fast; the honest
  UNKNOWN covers everything past it. (Length-based detection can false-positive at exactly 100, which
  errs toward UNKNOWN, the safe direction. Never a false clear.)

### `connectors/forge_review.py`
- `normalize_forge_review_prs(..., coverage_truncated: bool = False)`. When True, the single forge
  review `source_status` is `"stale"` (not `"fresh"`) with a plain `safe_user_message`, e.g.
  "Checked the most recent 100 open PRs; there are more open PRs not included, so this is not a
  complete check." The collision cards are emitted exactly as today.
- `run_github_pr_probe` threads `truncated` from the fetch into the normalize call.

## Non-goals (sequenced, not cut)

- **Precise truncation copy.** Today truncation routes through `incomplete[stale-dep]`, which the M2
  render shows as "couldn't reach GitHub" (imprecise: we did reach it). The correct fix is to wire the
  reserved `incomplete[unbounded]` reason (select.py:382) end to end to a distinct render line
  ("checked the most recent N open PRs; more exist"). That touches the core closure + assessment +
  render and gets its own reviewed slice. The false clear is gone now; the copy precision follows.
- **Path-filtered server-side PR search** (so very busy repos get a real conflict answer instead of
  UNKNOWN) is a future connector enhancement.
- **Full pagination beyond one page** is deliberately not done (hook latency); honest UNKNOWN covers it.

## Testing
- Truncated PR list (100 PRs, none colliding) -> forge-review status `stale` -> conflict verdict
  UNKNOWN (not clear) through the real broker.
- Truncated list WITH a colliding PR in the page -> the collision card is still present (found).
- Not truncated (< 100 PRs, none colliding) -> status `fresh` -> conflict can be clear.
- A single PR with a full (100) file list -> `truncated` True.
- `fetch_github_pull_requests` returns the truncation flag; `run_github_pr_probe` threads it; existing
  github/forge tests stay green. Zero em dashes.
