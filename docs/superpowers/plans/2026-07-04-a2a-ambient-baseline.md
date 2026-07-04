# A-2a: The Ambient Baseline Engine Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** The hook stops being once-per-session: every edit event consults a per-session baseline, re-checks the world no more often than the interval, is silent only when the silence law allows, and on any content change speaks the full current answer. (The delta VOICE and the UserPromptSubmit moment are A-2b; this slice makes re-speak-on-change the interim utterance, which is honest and complete on its own.)

**Architecture:** BINDING design: `docs/superpowers/specs/2026-07-04-ambient-delta-engine.md` REVISION 2 sections 1, 2, 3, 6 (every pin is law: the digest field enumeration incl. exclusions; per-session state files with corrupt-is-NONE, eviction, ensure-ignore, env seams, injectable now; the baseline classes with precedence transition-speak > interval-silence > re-statement-timer and re-statement = max(15min, interval); the cost claim). Section 4 (deltas) and section 5's UserPromptSubmit are OUT of scope here; section 5's empty-path fixes are already on main (A-1).

**Branch:** worktree `git worktree add ../teamctx-a2a -b feat/ambient-baseline main`. Gates as separate commands with real exit codes; the offline emulation matrix must stay 12/12 (rows drive the hook with fresh sessions, so once-per-session removal must not break them; if a row asserts marker behavior, fix the row and record it); coverage >= 90.

### Task order (TDD per task, commit per task)
1. **`core/content_digest.py`** exactly per spec section 1 (signature takes signals,
   statuses, closure, authority; pre-delta by exclusion of changed_since_start; structured
   status facts only, safe_user_message excluded; canonical-JSON item sort; sha256). The
   full mutation test matrix (one per included field changes, one per excluded field does
   not). Purity test covers the module. Commit:
   `feat(core): the content-identity digest (what counts as change)`
2. **`src/teamctx/ambient.py`**: per spec section 2. Import-light (no onboard/connector
   imports; local atomic-write helper). API (pinned):
   `load_baseline(state_dir, session_id, key) -> Baseline | None` (corrupt-is-NONE at the
   read site), `store_baseline(...)` (atomic, 0600, evict files older than 7 days,
   ensure-ignore on first write), `compute_key(...)` over the spec's enumerated tuple
   (config bytes + authority bytes hashed together; teamctx version), and
   `decide(baseline, now, interval, content_digest, class_of_answer) -> Decision` where
   Decision is one of speak_full / silent / recheck_due, implementing the class machine
   (GOOD / GAP-KNOWN / NONE), never-downgrade, and re-statement = max(900s, interval)
   evaluated only after a real re-check. `TEAMCTX_AMBIENT_STATE` and
   `TEAMCTX_AMBIENT_INTERVAL_SECONDS` (default 90, floor 30) read at call time; `now` is a
   parameter everywhere (injectable). Tests: the full class-transition matrix from the spec
   test bar, eviction, corruption, key isolation (branch, superset paths, config edit,
   authority edit, version, session). Commit:
   `feat(ambient): per-session baselines, the silence law, one owner of hook state`
3. **hook.py rework**: the `/tmp` marker machinery is DELETED (functions, env var use,
   tests). `_run` handles every Edit/Write/MultiEdit event: resolve inputs as today, compute
   the key, consult ambient: NONE -> ground, speak full, store (class per answer);
   interval-not-expired -> exit silent (legal only per the stored class; a stored non-good
   class whose gap was already surfaced THIS SESSION is silent per GAP-KNOWN);
   expired -> re-ground, compare digests: same -> update timestamps, silent (or re-state the
   same gap when the re-statement period elapsed); different -> speak the FULL current
   answer, store the new baseline. Re-check failure never downgrades GOOD (spec 3). The
   fail-safe stays absolute: any error exits 0 silently and leaves state untouched.
   Tests rewritten from the marker tests: same-session second edit inside the interval is
   silent; after (injected) expiry with changed mock world it speaks; unchanged world stays
   silent; a GAP baseline re-states after max(15m, interval); corrupt state file grounds
   fresh. Commit: `feat(hook): continuous grounding under the silence law (the marker dies)`
4. **CHANGELOG** (Added):
   `- The pre-edit check is now continuous: it quietly re-checks at an interval (default 90s) and speaks again only when the answer actually changed or a known gap needs re-stating; silence now means "checked, nothing new", never "not looking".`
   Full gate + em-dash grep + `python emulation/runner.py --offline --all` 12/12. Commit:
   `docs(changelog): continuous ambient grounding`

## Completion
Stop after the last commit. Do NOT merge, push, or remove the worktree. Report: branch,
commits, gate exit codes, matrix status, files changed, deviations.
