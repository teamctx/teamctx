# Spec: S8, collision at scale: GraphQL batching + honest unbounded coverage

## Status
Revision 1, proposed by the CTO 2026-07-03; adversarial review before build. Closes F7 (the
hook's unbounded 1+N wall-clock) and the truncation-copy follow-up (a truncated PR list
currently renders as "couldn't reach GitHub", which is false). Corrects the plan's earlier
framing: GitHub offers NO server-side path filter over open-PR files, so the honest design is
batched enumeration with an explicit budget and first-class partial-coverage semantics.

## Design

### 1. One GraphQL request per 100 PRs (replaces 1+N REST)
The work-start collision probe switches to the GitHub GraphQL API (same token, endpoint
`https://api.github.com/graphql`):

```graphql
query($owner:String!, $name:String!, $cursor:String) {
  repository(owner:$owner, name:$name) {
    pullRequests(states:OPEN, first:100, after:$cursor,
                 orderBy:{field:UPDATED_AT, direction:DESC}) {
      nodes {
        number url createdAt updatedAt headRefName
        headRepository { nameWithOwner }
        files(first:100) { nodes { path } pageInfo { hasNextPage } }
      }
      pageInfo { hasNextPage endCursor }
    }
  }
}
```

Own-PR rule unchanged (headRefName + headRepository.nameWithOwner map onto the existing
fields). ONE collision path: the REST PR-list/files fetchers are deleted and the dev probe
`github-pr-probe` rides the same GraphQL fetch (no dual maintenance; the REST `get_json`
helper remains for checks/issues). Malformed GraphQL payloads, GraphQL `errors` entries, and
HTTP failures all route to the existing unavailable document (fail closed, tested per shape).

### 2. Budgets, pinned
- Full profile: up to 3 pages (300 most-recently-updated open PRs).
- Reflex profile (the hook): 1 page, PLUS the hook's existing 8s socket bound now covers a
  bounded request count by construction (F7 closed: worst case is one GraphQL round-trip).
- `pullRequests.pageInfo.hasNextPage` true past the budget -> coverage is UNBOUNDED (below).
- A PR whose `files.pageInfo.hasNextPage` is true and whose first 100 files show NO overlap
  cannot be cleared: it contributes unbounded coverage (its files were not exhausted). A PR
  whose first 100 files DO overlap fires normally (a finding needs one witness; coverage of
  the rest is irrelevant to that finding).

### 3. `incomplete[unbounded]` end to end (the honesty payload)
- `SourceStatusValue` gains `"unbounded"` (additive): the source responded correctly but the
  result space exceeds the budget; distinct from `stale` (which keeps meaning old/degraded
  data) and from `unavailable`.
- The forge status emits `unbounded` with the message naming the numbers: `Checked the {n}
  most recently updated open PRs; more exist, so this is not a complete check.` (also used
  for the per-PR files case, with its own wording naming the PR).
- `assess_completeness`: a mandated family whose worst present status is `unbounded` (no
  stale/unavailable/blocked/disabled present) -> `incomplete[unbounded]` (the reserved reason
  finally emitted). Precedence: real unreachability still dominates (any
  stale/unavailable/blocked -> stale-dep as today); `unbounded` outranks pending and
  not_applicable.
- `assessment.CheckStatus` gains `"unbounded"`; kind mapping: an unbounded IMPORTANT check ->
  `cant_verify` (you cannot rely on the clear you did not get), any unbounded check is never
  `clear`.
- Render: a `Partially checked:` line (sibling of `Couldn't check:`): for conflict:
  `open PRs (checked the {n} most recently updated; more exist)`; the note from the coverage
  entry is preferred verbatim when present (S5a note plumbing). Hook can't-verify copy for
  the unbounded conflict case: `teamctx checked the {n} most recently updated open PRs and
  found no collision, but more open PRs exist; on a repo this busy, glance at GitHub if this
  file is sensitive.` The old false "couldn't reach GitHub" copy for truncation dies.
- The GitHub checks probe's existing truncation keeps `stale` for now (its `total_count`
  detection is exact and rare); migrating it to `unbounded` is included IF the diff stays
  small, else deferred openly in the plan.

### 4. What does NOT change
Core evaluate logic (closure reasons already flow), the own-PR FYI, the GitLab plan (S9
mirrors `unbounded` semantics with REST budgets), CLI flags (none added).

## Test bar
GraphQL payload parsing incl. malformed shapes and `errors`; page-budget matrix (under, at,
over budget; per-PR files overflow with and without overlap); profile budgets (reflex 1 page);
`unbounded` precedence in assess_completeness (vs stale, pending, disabled, not_applicable);
assessment kind mapping (important unbounded -> cant_verify); render + hook copy exact;
e2e: 301 fabricated PRs -> "Partially checked" with n=300 and no clear; dev probe parity.
