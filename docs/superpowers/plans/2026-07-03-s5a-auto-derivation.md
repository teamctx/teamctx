# S5a: Issue + Since Auto-Derivation Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** The criteria check fires with zero flags: linked issues derive from the branch name and local commit trailers, `since` derives from the merge-base timestamp, derived inputs carry visible provenance bound into the replay digest, and every skipped connector's reason reaches the render as a precise in-band note (kills F9 and F13).

**Architecture:** BINDING design in `docs/superpowers/specs/2026-07-03-autodiscovery-and-structure.md` section S5a (revision 2: pinned regexes, precedence, privacy boundary, provenance carrier, disabled-status mapping). New read-only-git `discover.py`; `parse_since` in `clock.py`; `RequestContext.input_provenance` + `BrokerAnswer.request` carry provenance to the render; the runner emits `disabled` SourceStatuses for skipped connectors; `CheckState.note` routes them to the "Not checked:" line via each kind's `deps_family`.

**Branch:** worktree `git worktree add ../teamctx-s5a -b feat/auto-derivation main`, all work inside it. Gate per commit: `python -m pytest -q -p no:cacheprovider && ruff check src tests && python -m mypy src` and `grep -rP '\x{2014}' src tests` empty.

**Pinned user-facing copy (verbatim; the CTO owns these strings):**
- disabled note, criteria, nothing derived: `spec changes (no issue could be derived from your branch or commits; name one with --issue)`
- disabled note, criteria, issue derived but no since: `spec changes (issue {refs} was derived, but the start time couldn't be; pass --since)`
- disabled note, docs: `docs (no docs root is configured; set work_start.docs_root to enable)`
- disabled note, gate: `failing checks (couldn't determine your branch; pass --branch or --ref)`
- criteria clear-line provenance suffix: single issue `(issue #123 from your branch name)` or `(issue #123 from a commit trailer)`; multiple `(issues #12 from your branch name, #34 from a commit trailer)`; explicit issues get NO suffix.
- since provenance value (in `input_provenance["since"]`): `when you branched (merge-base {shortsha})`
- unparseable explicit since error: `--since {value!r} is not an ISO-8601 timestamp (e.g. 2026-07-01 or 2026-07-01T12:00:00Z).`
- cap note (appended to the derived-issues provenance when >5 found): the first 5 numerically are used and the disabled/derived note says `capped at 5 issues; pass --issue to name others`.

---

### Task 1: discover.py (TDD; the spec's regexes are law)

**Files:** Create `src/teamctx/discover.py`, `tests/test_discover.py`.

```python
def derive_issues(root: Path) -> tuple[tuple[str, str], ...]:
    """((issue_ref, provenance), ...) e.g. (("#123", "your branch name"),). Union of branch +
    trailer derivation, deduped (branch wins provenance on a tie), numerically sorted, capped
    at 5 (cap recorded by derive_issues_capped flag; see below)."""

def derive_since(root: Path) -> tuple[str, str] | None:
    """(iso_utc, provenance) from the merge-base committer timestamp, or None (honest absence)."""
```

Implementation notes (binding): branch regex `(?:^|[/_-])#?(\d{1,6})(?=[/_-]|$)` with the
`v`/`V`-prefix rejection; trailer regex `\b(?:fixes|closes|resolves)\s+#(\d{1,6})\b` (case-
insensitive) over `git log --format=%B {merge_base}..HEAD`; default branch via
`git symbolic-ref --short refs/remotes/origin/HEAD` then existing `origin/main` then
`origin/master`; every git call through a `_run_git` mirroring git_context.py (timeout 10,
None on any failure). Return the cap as part of the tuple design: make `derive_issues` return
a small frozen dataclass `DerivedIssues(issues=..., capped=bool)` if cleaner; pin: the cap
fact must reach the runner. `since` = `git show -s --format=%cI {merge_base}` normalized to
UTC ISO.

- [ ] Tests first, the spec's matrix: branch `123-fix`, `feat/123-x`, `issue-123`, `fix/#123`
  derive `#123`; `v2`, `release-2.0`, `feature` derive nothing; trailers multi-issue union +
  dedupe + numeric sort; >5 issues capped with `capped=True`; no default branch, detached
  HEAD, non-git dir all give honest absence; since equals the merge-base commit's timestamp
  (create real tmp git repos in tests, the repo's test suite already does this in
  test_git_context.py, follow it).
- [ ] Implement; full gate; commit `feat(discover): derive linked issues and since from branch and local trailers`.

### Task 2: parse_since in clock.py (kills F13)

**Files:** Modify `src/teamctx/clock.py`, `src/teamctx/connectors/github_issues.py`; `tests/test_clock.py`, `tests/test_github_issues.py`.

- [ ] `parse_since(text: str) -> datetime` via `datetime.fromisoformat` (3.12 handles `Z`);
  naive input assumed UTC; date-only accepted (midnight UTC); raises `ValueError` with the
  pinned copy on failure. The issue connector's `updated_at <= since` and event `created_at
  <= since` comparisons route through `parse_since` on BOTH sides (GitHub timestamps are
  Z-ISO; a parse failure on the GitHub side falls back to surfacing the change rather than
  dropping it, fail closed toward noise not silence). Tests: Z vs offset vs date-only, and
  the fail-closed GitHub-side fallback.
- [ ] Full gate; commit `fix(issues): one since parser; comparisons are chronological, never lexical (F13)`.

### Task 3: Provenance carriers (contracts + broker + resolve)

**Files:** Modify `src/teamctx/core/contracts.py` (RequestContext), `src/teamctx/core/broker.py` (BrokerAnswer + both answer builders), `src/teamctx/runner.py` (WorkStartInputs + build_request_context), `src/teamctx/resolve.py`; tests: `tests/test_core_contracts.py`, `tests/test_broker.py`, `tests/test_resolve.py`.

- [ ] `RequestContext` gains `input_provenance: dict[str, str] = Field(default_factory=dict)`
  (additive; extra=forbid unaffected). `WorkStartInputs` gains
  `input_provenance: tuple[tuple[str, str], ...] = ()`; `build_request_context` copies it in
  as a dict. `BrokerAnswer` gains `request: RequestContext`; `broker_answer` passes it
  (positional arg already present); check every BrokerAnswer construction site (grep) incl.
  eval/pack.
- [ ] `resolve_work_start_inputs`: when `issues` is empty, call `derive_issues`; when `since`
  is None, call `derive_since`; explicit values DISABLE the respective derivation entirely
  (spec precedence); explicit `since` is validated through `parse_since` here, raising
  `WorkStartResolutionError` with the pinned copy. Provenance entries: `"issue:{ref}"` and
  `"since"` per spec. The criteria connector still requires BOTH issues and since (unchanged
  runner gate).
- [ ] Tests: derived issues + since flow into RequestContext.input_provenance and the digest
  changes when provenance does (assert two selections differ); explicit flags suppress
  derivation; bad explicit since raises the pinned message.
- [ ] Full gate; commit `feat(resolve): derive issues and since with visible provenance bound into the request`.

### Task 4: Disabled statuses from the runner (kills F9)

**Files:** Modify `src/teamctx/runner.py`, `src/teamctx/core/select.py` (assess_completeness); tests: `tests/test_runner.py`, `tests/test_select.py`.

- [ ] For each connector the runner skips, emit a one-status `CoreContractDocument` (reuse
  `connectors/_contract.unavailable_document` with `status="disabled"`,
  visibility `"warning_when_relevant"`) whose `safe_user_message` is the pinned copy above:
  issue_tracker (two variants: nothing derived vs issue-derived-but-no-since, and append the
  cap note when capped), docs, ci_deploy. Source ids: `github_issues`, `docs_supersession`,
  `github_check_runs` (match the real connectors' ids so coverage families line up).
- [ ] `assess_completeness`: a mandated family whose present entries are ALL `disabled` maps
  to `incomplete[policy-gap]` (never stale-dep). Any mix containing a non-disabled unhealthy
  status keeps today's stale-dep behavior. Tests for both.
- [ ] Full gate; commit `feat(runner): skipped connectors leave an in-band disabled status naming the exact missing input`.

### Task 5: Notes reach the render; provenance reaches the clear line

**Files:** Modify `src/teamctx/assessment.py`, `src/teamctx/contract_render.py`; tests: `tests/test_assessment.py`, `tests/test_render_broker_answer.py`.

- [ ] `CheckState` gains `note: str | None = None`. `assess()` fills it for `not_configured`
  checks from the `disabled` coverage entry whose `source_family` equals the kind's
  `deps_family` (import the mapping from `core.kinds`; multiple entries join with `"; "`).
  `_not_checked_line` uses `state.note` when set, else the static `RENDER_COPY` fallback.
- [ ] Criteria clear line: when the check is `clear` and `answer.request.input_provenance`
  has `issue:` entries, append the pinned provenance suffix to the criteria clear phrase.
  Explicit (no provenance) renders exactly as today.
- [ ] Tests: disabled note appears verbatim in "Not checked:"; both criteria-note variants;
  provenance suffix single + multiple + absent-for-explicit; hook signal unchanged for these
  cases (its clear line does NOT carry the suffix; assert that).
- [ ] Full gate; commit `feat(render): precise not-run reasons and derived-input provenance on the criteria line`.

### Task 6: End-to-end + CHANGELOG

- [ ] End-to-end test (new `tests/test_auto_derivation_e2e.py`): a real tmp git repo with
  branch `42-fix-auth`, one commit after branching from main, fake GitHub opener for the
  issues probe: `work_start_answer` with only paths+repo+token fires the criteria connector
  for `#42` with a derived since, and the render shows the provenance suffix. Second e2e: no
  derivable issue, the render's "Not checked:" carries the pinned derive-nothing copy.
- [ ] CHANGELOG under Added: `- work-start now derives the linked issue and the start time from your branch name, local commit trailers, and the merge-base, with the derivation named in the output; explicit --issue/--since override it.` Under Fixed: `- A skipped check now says exactly which input is missing and how to provide it, and issue-change time comparisons are chronological, never lexical.`
- [ ] Full gate + coverage still >= 90 (`python -m pytest -q -p no:cacheprovider --cov | tail -2`). Commit `docs(changelog): auto-derivation slice`.

## Completion
Stop after the last commit. Do NOT merge, push, or remove the worktree. Report: branch, commits, gate tail, files changed, deviations with reasons. The CTO reviews and merges.
