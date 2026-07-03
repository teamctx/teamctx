# S8: Bounded Collision at Scale Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** The collision probe moves to GitHub GraphQL batching (one request per 100 PRs including files) with pinned budgets and a reflex profile, and partial coverage becomes first-class end to end (`unbounded` status -> `incomplete[unbounded]` -> "Partially checked:" line), per the review-hardened spec.

**Architecture:** BINDING design with every seam enumerated:
`docs/superpowers/specs/2026-07-03-s8-bounded-collision-scale.md` (revision 2). The spec's
pins are law, especially: the P0 GraphQL errors-before-data precedence with NO partial
salvage; the own-PR partition running before the unbounded-files rule; BOTH lockstep
assessment edits; the exact assess_completeness exclusion set and branch position; the note
plumbing and the cant_verify bullet/no-double-print rules; all user-facing copy verbatim
from the spec.

**Branch:** worktree `git worktree add ../teamctx-s8 -b feat/bounded-collision main`. Gate
per commit: `python -m pytest -q -p no:cacheprovider && ruff check src tests && python -m
mypy src` and `grep -rP '\x{2014}' src tests` empty; final commit also checks coverage >= 90.

### Task order (TDD per task, commit per task)
1. **`graphql_json` helper + the P0 boundary** (connectors/github.py): the POST helper and a
   `fetch_github_pull_requests_graphql(repo, token, include_titles, max_pages, opener)`
   returning the existing `ForgeReviewFetch` shape extended with
   `unbounded_list: bool` and `unbounded_files_prs: list[int]` (replacing the single
   `truncated` bool; forge_review normalization consumes the new fields). Tests FIRST, one
   per P0 shape (spec section 1), then healthy single/multi-page shapes, the exactly-100-
   with-hasNextPage-false boundary, and the P1-7 page-2-failure discard.
   Commit: `feat(github): GraphQL PR fetch with errors-before-data fail-closed boundary`
2. **Profile threading** (runner.py WorkStartInputs.profile, hook.py `_ground` sets reflex,
   run_work_start_connectors computes max_pages 1/3 and passes it through
   run_github_pr_probe). Tests: reflex = exactly one page request (count requests via a
   capturing opener); full = up to 3. Commit: `feat(runner): reflex/full profile budgets; hook is one round-trip (F7)`
3. **Unbounded through forge_review** (own-PR partition FIRST, then unbounded-files; the
   two verbatim messages + concatenation; status "unbounded"; contracts SourceStatusValue
   gains "unbounded"). Tests incl. the own-200-file-PR case. Commit:
   `feat(forge-review): unbounded coverage recorded honestly; own PRs never contribute it`
4. **Core + assessment** (select.assess_completeness exact edit; assessment BOTH sites;
   CheckStatus "unbounded"; _note_for extension). Tests: the precedence combos and both
   lockstep-miss regressions from the spec. Commit:
   `feat(core): incomplete[unbounded] emitted and classified, never a clear`
5. **Render + hook** (the Partially checked line, the cant_verify bullet, no-double-print,
   never-empty-headline, hook unbounded branch; copy verbatim from spec section 3). Commit:
   `feat(render): partially-checked surfacing; the false couldn't-reach truncation copy dies`
6. **REST deletion + dev probe parity** (delete the REST PR fetchers, github-pr-probe rides
   GraphQL, --include-title gated title selection; sweep for dead code). e2e: 301 PRs ->
   n=300 partial, never clear. CHANGELOG (under Changed):
   `- The collision probe now fetches open PRs in batched GraphQL pages with a pinned budget; a repo busier than the budget reads "Partially checked", never a false "couldn't reach GitHub" and never a silent clear. The pre-edit hook is a single round-trip.`
   Commit: `refactor(github): one GraphQL collision path; REST PR fetchers removed`

## Completion
Stop after the last commit. Do NOT merge, push, or remove the worktree. Report: branch,
commits, gate tail, files changed, deviations with reasons. On a plan-vs-code contradiction,
stop that task and record it.
