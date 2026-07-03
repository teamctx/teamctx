# S10: Jira Criteria Connector Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Jira becomes a live second issue tracker: `PROJ-123` refs derive from branches and trailers, changes since the merge-base fire criteria with field-level detail, and every fail-closed pin from the review-hardened spec holds (an unconfigured-Jira KEY-N or a mixed `#N`+`KEY-N` family can never read clear off the GitHub side alone).

**Architecture:** BINDING design: `docs/superpowers/specs/2026-07-03-source-breadth.md` REVISION 2 section 3 (ref-dispatch span-removal regexes, the unconfigured-Jira disabled emission, the fail-closed change-detection pins, the normalize channels P1-4, browse-URL scope) + these plan pins:
- New `src/teamctx/connectors/jira.py`: `run_jira_issues_probe(base_url, issues, since, auth, request_context, observed_at, opener)`. Auth = `tokens.resolve_atlassian_auth()` (exists since S9a); base_url from `config.work_start.jira.base_url` (this IS the harness seam: the mock server address goes in config; no new env var). Requests: `GET {base}/rest/api/3/issue/{key}?fields=summary,status,labels,updated` then `GET {base}/rest/api/3/issue/{key}/changelog?maxResults=100`, basic auth header built from the pair, `Accept: application/json`.
- **Field-level classification:** changelog items after `since` (chronological via `parse_since`, both sides): `field=="description"` -> body_edited; `"status"` -> state_changed; `"labels"` -> labels_changed; other fields counted as `body_edited` only when NOTHING else matched and `updated > since` (mirrors the GitHub fallback). All the spec's fail-closed pins: missing/unparseable `updated` -> Jira source `stale`; changelog fetch failure on a known-changed issue -> the signal still fires with generic detail; absent/malformed `isLast` -> NOT last -> `stale`.
- **Runner dispatch (pinned):** derived/explicit issues split SYNTACTICALLY: `#N`/bare-N -> the forge tracker (github probe when forge==github; for gitlab forge they stay disabled as S9a pinned); `KEY-N` -> the Jira probe when `jira` config exists, else the S9a-style `disabled` emission with the spec's verbatim note (`issue {refs} looks like a Jira issue, but no Jira is configured; add work_start.jira to .teamctx/config.json`). Both kinds present -> both probes run -> two `issue_tracker` family entries; the closure's worst-status rule keeps mixed families honest (test the spec's {fresh(github), disabled(jira)} -> stale-dep case AND {fresh, fresh} -> complete).
- **discover.py (spec regexes verbatim):** the Jira-key regex runs FIRST with span-removal before the numeric regex; trailers accept Jira keys after closing keywords. Provenance strings unchanged in form: `("PROJ-123", "your branch name")`.
- **normalize channels (P1-4):** `normalize_issue_changes` gains `source_id: str` and `coverage_truncated: bool`; `IssueCriteriaChange` gains `source_display: str` (GitHub fills `GitHub Issue #5: {title}`, Jira fills `Jira PROJ-123: {summary}`) and `url` already rides scope for open-source.
- **Copy (verbatim, CTO-owned):** no-credential: `Jira is configured but no Atlassian credential was found. Set ATLASSIAN_EMAIL and ATLASSIAN_API_TOKEN (or ATLASSIAN_API_TOKEN_FILE).` · half-credential: `Jira is configured but only half the Atlassian credential is set; both ATLASSIAN_EMAIL and ATLASSIAN_API_TOKEN are needed.` · unreachable: `Jira is unavailable with current access.` (401/403/404 variants mirror GitHub's granularity) · stale-history: `Checked the most recent 100 changes on {key}; more history exists, so this is not a complete check.` · malformed-updated: `Jira returned an unreadable update time for {key}; its criteria state can't be confirmed.`
- `finding_query`: `issue:` selector matches Jira keys case-insensitively without requiring `#`.

**Branch:** worktree `git worktree add ../teamctx-s10 -b feat/jira-connector main`. Another builder is active in ../teamctx-p5b; never touch it or main. Gates as SEPARATE commands with real exit codes; final task adds coverage >= 90. No live network calls; injected openers only.

### Task order (TDD per task, commit per task)
1. discover.py Jira-key dispatch (spec regexes, span-removal, trailer keys; the spec's test
   trio `PROJ-123`, `PROJ-123-fix`, `feat/ABC-7` plus mixed-branch cases). Commit:
   `feat(discover): jira keys derive first with span removal; numerics never double-fire`
2. normalize channels + `source_display`/truncation parameterization, GitHub caller updated
   byte-identically (its tests unchanged except constructor fields). Commit:
   `feat(issue-criteria): provider channels for display, id, and truncation honesty`
3. `connectors/jira.py` fetch + classification + every fail-closed pin, test-per-pin.
   Commit: `feat(jira): criteria probe with field-level detail, fail closed everywhere`
4. Runner dispatch + the unconfigured-Jira disabled emission + mixed-family tests + the
   half-credential path. Commit: `feat(runner): syntactic tracker dispatch; mixed families stay honest`
5. e2e (tmp git repo, branch `PROJ-123-fix`, fake opener: changed description fires with
   `Jira PROJ-123:` display and the provenance suffix; unconfigured variant reads the
   disabled note and never clear) + CHANGELOG (Added):
   `- Jira support: acceptance-criteria changes on PROJ-123 style issues derived from your branch or commits, with field-level change detail, alongside GitHub issues in one honest coverage picture.`
   Commit: `test(jira): end-to-end criteria; changelog`

## Completion
Stop after the last commit. Do NOT merge, push, or remove the worktree. Report: branch,
commits, gate exit codes, files changed, deviations. On plan-vs-code contradiction, stop
and record.
