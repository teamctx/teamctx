# S9b: GitLab Connector Implementation Plan (collision + gate)

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** GitLab repos get live collision and gate checks with the same honest-coverage behavior GitHub proved: own-MR FYI, unbounded budgets, the pinned never-clear pipeline mapping, MR terminology everywhere a human reads.

**Architecture:** BINDING design: `docs/superpowers/specs/2026-07-03-source-breadth.md` REVISION 2 section 2 (the P0 pipeline invariant, own-MR rule, provider/source_id parameterization, terminology dispatch, `scope["provider"]` render gating) + these plan-level pins:
- **Budgets (REST is 1+N):** MR list pages: `max_pages` from the profile exactly like GitHub (reflex 1, full 3; `x-next-page` header or full page -> more exist). Per-MR diffs: fetched most-recently-updated first, capped at 20 MRs in reflex and 100 in full; MRs beyond the diff budget (that are not own-MRs) contribute UNBOUNDED coverage with the message `Checked the files of the {k} most recently updated open MRs; {m} more open MRs were not file-checked.` A single MR whose diffs page is full (100) and shows no overlap contributes unbounded (mirrors S8's per-PR rule; own-MRs partitioned FIRST, never contributing).
- **`RequestContext` gains `forge: str = "github"`** (additive; digest-covered; resolve fills it). The render's conflict-check copy dispatches on it: clear phrase `no other open MRs touch your files`, unreachable phrase `open MRs (couldn't reach GitLab)`, hook phrases likewise (`no other open merge requests touch these files`, gap `open merge requests`). CheckCopy grows optional gitlab variants for the conflict and gate checks ONLY where wording differs (gate unreachable: `pipeline state (couldn't reach GitLab)`); everything else stays shared.
- **`TEAMCTX_GITLAB_API_ROOT`** env override mirroring the GitHub seam (default `https://gitlab.com`), same call-time read, same conftest autouse clearing, same token-sensitivity docstring note.
- **Unavailable copy (verbatim):** `GitLab MR metadata is unavailable because no token is configured.` / `CI status is unavailable because no token is configured.` (shared gate wording), no-token fix text in the render: the existing GitHub fix line gains a GitLab twin `set GITLAB_TOKEN, or GITLAB_TOKEN_FILE with a path to a token file` selected by forge.
- **Gate zero-pipelines note (verbatim, from the spec):** `no pipeline ran for this branch, so the gate is unverified`.

**Branch:** worktree `git worktree add ../teamctx-s9b -b feat/gitlab-connector main`. Another builder may be active in ../teamctx-p5; never touch it or main. Gate per commit, with REAL exit codes (no pipe-masking): run `python -m pytest -q -p no:cacheprovider`, `ruff check src tests`, `python -m mypy src`, and `grep -rP '\x{2014}' src tests` as separate commands and confirm each exit status; final task adds the coverage check.

### Task order (TDD per task, commit per task)
1. **`connectors/gitlab.py` fetchers**: `gitlab_api_root()`, URL-encoded project slug
   (`quote(slug, safe="")`), MR list with pagination/budget, per-MR diffs with the diff
   budget, own-MR fields (`source_branch`, `source_project_id`, `target_project_id`),
   fail-closed parsing (malformed payloads/pagination -> `GitLabProbeError` -> unavailable;
   mirror github.py's shapes test-for-test). Commit:
   `feat(gitlab): MR fetch with budgets and fail-closed boundaries`
2. **Collision probe + normalization**: `run_gitlab_mr_probe` feeding
   `normalize_forge_review_prs(provider="gitlab", source_id="gitlab_mr_metadata")`; the MR
   terminology dispatch in forge_review (`GitLab MR !12`, `Open MR !12 changed ...`,
   own-MR FYI wording reuses the existing sentence with MR/`!` forms); `scope["provider"]`
   on forge cards; `_gh_hint` and `render_open_source` gated to github (GitLab shows
   `web_url`). Commit: `feat(gitlab): collision through the one forge pipeline, MR-worded`
3. **Gate probe**: `run_gitlab_pipeline_probe` implementing the spec's pinned mapping table
   (success/pending-set/failed+canceled with the synthetic `pipeline {status}` gate when no
   failed job/skipped+manual+unknown -> stale/zero-pipelines -> disabled note). A
   parameterized test asserts NO non-success status can reach a clear verdict. Commit:
   `feat(gitlab): pipeline gate with the never-clear invariant`
4. **Runner + resolve wiring**: forge=="gitlab" dispatches to the two GitLab probes with
   `resolve_token("GITLAB_TOKEN")` (replacing the unwired disabled notes and their tests);
   `RequestContext.forge` filled by resolve; issues stay disabled for gitlab (unchanged
   S9a note; Jira arrives in S10). Commit: `feat(runner): gitlab forge dispatch, live`
5. **Render forge dispatch**: the CheckCopy gitlab variants + hook wording + the no-token
   fix line by forge; regenerate nothing in README yet (S11's slice will refresh docs).
   Commit: `feat(render): MR-worded conflict and gate copy for gitlab repos`
6. **e2e + CHANGELOG**: an e2e mirroring test_auto_derivation_e2e with a gitlab-origin tmp
   repo and a fake opener: colliding MR fires MR-worded card; own-MR FYI; canceled-pipeline
   synthetic gate; zero-pipelines disabled note. CHANGELOG (Added):
   `- GitLab support: open merge requests (collisions, with the own-MR FYI) and pipeline state (never assumed green) for repos whose origin is gitlab.com, with the same honest budgets and coverage reporting as GitHub.`
   Commit: `test(gitlab): end-to-end MR collision and pipeline gate; changelog`

## Completion
Stop after the last commit. Do NOT merge, push, or remove the worktree. Report: branch,
commits, gate exit codes, files changed, deviations. On plan-vs-code contradiction, stop
and record.
