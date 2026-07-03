# Spec: S8, collision at scale: GraphQL batching + honest unbounded coverage

## Status
Revision 2, after an Opus 4.8 adversarial spec review (verdict on rev 1: REVISE-FIRST; one
P0, seven P1, five P2, all accepted and pinned below; two "verified-safe" notes recorded so
the builder does not over-engineer). Ready to build. Closes F7 and the truncation-copy
follow-up. **Sequencing correction (review P1-1): the `profile` field is INTRODUCED HERE,
not in S9a; the source-breadth spec inherits it.**

## Design

### 1. One GraphQL request per 100 PRs (replaces 1+N REST)
Query as rev 1 (`repository.pullRequests(states:OPEN, first:100, orderBy UPDATED_AT DESC)`
with per-node `files(first:100)` and `pageInfo` at both levels), PLUS the P2-1/P2-2 pins:
- `title` is selected ONLY when `include_titles` is set (the flag stays honest, never a
  silent no-op); `state` is synthesized as `"open"` (all nodes are OPEN by query);
  `merged_at` is always None for open PRs; labels are NOT fetched (nothing renders them;
  the scope field is dropped from the GraphQL path and its absence documented).
- `headRepository: null` (deleted fork) parses to `head_repo=None` (never a crash; the PR
  is then never "own", fail-closed toward surfacing).

**The POST helper (P2-4, pinned):** a new `graphql_json(query, variables, token, opener)`
in connectors/github.py: POST to `https://api.github.com/graphql`, body
`{"query":..., "variables":...}`, headers `Authorization: Bearer`, `Content-Type:
application/json`, the existing User-Agent; no `X-GitHub-Api-Version`. JSON-decode failure
and HTTP errors raise `GitHubProbeError` exactly like `get_json` (which remains for
checks/issues REST).

**The one law at the GraphQL boundary (P0-1, pinned precedence):**
1. Any non-empty top-level `errors` array -> the unavailable document; `data` is DISCARDED
   entirely (no partial-node salvage). Optionally (P2-3) when every error has
   `type == "RATE_LIMITED"`, the rate-limit copy is used instead of the generic one.
2. `data` missing or null, `data.repository` null, `pullRequests` missing, or `nodes` not a
   list -> unavailable (a private/renamed repo is NEVER an empty clean scan).
3. Only then are nodes parsed; a malformed node fails closed to unavailable for the whole
   probe (a crash mid-parse must not leak a partial clean set).
Tests, one per shape: `repository:null`, `data:null`, partial-nodes-with-errors,
`nodes:[]`-with-errors, malformed node, plus the healthy shapes.

**Pagination failure (P1-7, pinned):** any page fetch failing at any depth -> unavailable,
accumulated pages DISCARDED. A real outage is never downgraded to `unbounded` (which reads
as a graceful budget cut). Stated openly: this discards a collision witness that page 1 may
have held; that is the correct trade (still non-clear, never a false clear).

### 2. Budgets and the profile field (P1-1, now in scope here)
- `WorkStartInputs` gains `profile: Literal["full", "reflex"] = "full"` (moved into S8 from
  the source-breadth spec, which now inherits it). The hook sets `profile="reflex"` in
  `_ground`. Threading, pinned: `run_work_start_connectors` computes
  `max_pages = 1 if inputs.profile == "reflex" else 3` and passes it to
  `run_github_pr_probe(..., max_pages=...)` -> `fetch_github_pull_requests(...,
  max_pages=...)`. F7 closes for real: the reflex path is one GraphQL round-trip, bounded
  by the hook's existing 8s socket timeout.
- List `hasNextPage` true past the budget -> UNBOUNDED coverage. Per-PR files
  `hasNextPage` true with NO overlap in the first 100 -> unbounded coverage; WITH overlap
  -> the finding fires normally.
- **Own-PR ordering (P1-4, pinned):** the own-PR partition runs FIRST; an own-branch PR
  never contributes unbounded files coverage (it can never be a collision, so its
  unexhausted file list is irrelevant). The busy-repo author's own 200-file PR must not
  permanently can't-verify their own edits; test exactly this case.

### 3. `incomplete[unbounded]` end to end (seams enumerated, P1-2/3/5/6)
- `SourceStatusValue` gains `"unbounded"`. Verified-safe (recorded from review): the
  contracts fail-closed validators gate on `{disabled, blocked, unavailable}` only, so no
  validator change; signal freshness untouched.
- Forge status message, list case: `Checked the {n} most recently updated open PRs; more
  exist, so this is not a complete check.` (`{n}` = PRs actually fetched, owned by the
  CONNECTOR, never computed in the render). Files case: `Open PR #{num} changes more files
  than teamctx checked; it may touch yours.` **Both cases at once (P2-5): the messages
  concatenate in that order into the one status message** (matching the existing
  truncation+own-PR join pattern).
- `assess_completeness` (exact edit, P1-3): `"unbounded"` joins the first branch's
  exclusion set `{fresh, pending, not_applicable, disabled, unbounded}` AND a new branch
  `any(status == "unbounded") -> "incomplete[unbounded]"` inserted BETWEEN the stale-dep
  branch and the pending branch. Resulting precedence: stale/unavailable/blocked (and
  unknown strings) > unbounded > pending > not_applicable > disabled-all (policy-gap) >
  complete. Two-source combos tested: {stale,unbounded}->stale-dep;
  {fresh,unbounded},{disabled,unbounded},{pending,unbounded},{not_applicable,unbounded}
  ->unbounded.
- `assessment.py`, BOTH lockstep sites (P1-2): `_status_for` gains
  `reason "incomplete[unbounded]" -> "unbounded"` (else it falls to not_configured, a lie),
  AND the cant_verify kind set becomes `{"unreachable", "pending", "unbounded"}` (else an
  unbounded conflict alone reads "Looks clear to start.", a false clear on the flagship
  check). An unbounded check is never `clear`.
- **Note plumbing (P1-5, pinned mechanism):** `_note_for` extends to `status ==
  "unbounded"`: the note comes from the coverage entry of the check's deps_family with
  status `"unbounded"` (same join rule as disabled). The render prefers the verbatim note.
- **Render + hook seams (P1-6, pinned):** `_cant_verify_bullets` gains an unbounded bullet
  (parallel to the unreachable one, verbatim note + `Glance at GitHub if this file is
  sensitive.`); the new `_partially_checked_line` ("Partially checked: ...") skips
  important unbounded checks when `kind == cant_verify` (the `in_bullets` pattern of
  `_couldnt_check_line`), so nothing prints twice and the cant_verify headline can never
  sit with zero bullets. `hook_signal._cant_verify` gains an unbounded branch with the
  copy: `teamctx checked the {n} most recently updated open PRs and found no collision,
  but more open PRs exist. On a repo this busy, glance at GitHub if this file is
  sensitive.` (the numbers ride the coverage note verbatim).
- The GitHub checks probe keeps `stale` truncation for now; migrating it to `unbounded` is
  included only if the diff stays small, else deferred openly in the plan.

### 4. Dev probe parity
`github-pr-probe` rides the same GraphQL fetch (REST PR fetchers are deleted). Its
`--include-title` keeps working via the gated `title` selection.

## Test bar
Everything in rev 1, plus one test per P0 shape; the profile threading (hook sets reflex,
reflex = exactly one page request); own-PR-with-overflowing-files never unbounded; both
lockstep assessment edits; the precedence combos above; note plumbing verbatim; the
cant_verify bullet + no-double-print + never-empty-headline; hook unbounded copy;
boundary: exactly 100 items with `hasNextPage:false` is COMPLETE (the REST false-truncation
dies); e2e 301 PRs -> n=300 partial, never clear.
