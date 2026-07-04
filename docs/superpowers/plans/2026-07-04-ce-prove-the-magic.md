# C+E: Prove the Magic Implementation Plan (budgets pinned + delta evidence rows)

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** The ambient behaviors get the same committed proof as everything else: the silent path is provably zero-network, the re-check request budget is pinned as tests, and the emulation matrix grows four delta rows (appear, lawful silence, gap re-surface, reopened-PR re-speak), taking it to 16 rows.

**Architecture:** BINDING: the ambient plan rev 2 Workstreams C and E and the delta-engine spec rev 2 (its testability seams: `TEAMCTX_AMBIENT_STATE`, per-session state files whose JSON a row may back-date to cross the interval without sleeping). **Decision recorded (CTO): conditional REST requests (If-None-Match) are DEFERRED**: GraphQL (the dominant call) cannot use them, the benefit is rate-budget only, and ambient worst-case (~360 calls/hour/actor at the 30s floor) sits comfortably inside limits; building a response cache now is machinery without a bar to clear. The plan doc gains this note.

**Branch:** worktree `git worktree add ../teamctx-ce -b feat/prove-the-magic main`. Gates as separate commands with real exit codes; coverage >= 90; the matrix must end `16 PASS, 0 SKIP, 0 FAIL`.

### Task order (TDD per task, commit per task)
1. **Budget pins in the normal suite** (`tests/test_ambient_budgets.py`): (a) the silent
   path makes ZERO network calls (counting opener; second edit inside the interval) and
   returns in under 500ms (generous anti-flake bound; the path is pure file+compare); (b)
   the ambient re-check in reflex profile makes EXACTLY the pinned request count for a
   github repo with no issues/docs configured: one GraphQL POST + one checks GET (count via
   capturing opener); with issues configured: + the per-issue GETs. Commit:
   `test(ambient): the silent path is zero-network; re-check budgets pinned`
2. **Harness delta mode** (`emulation/actors.py` + a small `emulation/ambient_helpers.py`):
   a persistent-state actor mode (same session_id across invocations; `TEAMCTX_AMBIENT_STATE`
   kept across calls) and `backdate_baseline(state_dir, session_id, seconds)` that rewrites
   `last_network_check_at`/`last_spoken_at` in the state JSON (never sleeps). Commit:
   `feat(emulation): delta-mode actors (persistent session state, injected clock via backdate)`
3. **Row 13, the delta appears**: ground (clear world) -> second call same session, world
   gains a colliding PR, baseline back-dated past the interval -> the hook speaks EXACTLY
   the pinned appear line and NOT the steady bullet (suppression asserted). Row 14, lawful
   silence: unchanged world, back-dated -> empty additionalContext AND the verdict notes
   the silence is delta-dedup (assert the state file shows an updated
   last_network_check_at with an unchanged digest: silence-after-recheck, not skip). Commit:
   `feat(emulation): rows 13-14, the appear delta and lawful silence`
4. **Row 15, the gap re-surfaces**: ground with a good world -> world becomes unreachable
   (mock returns errors), back-dated -> speaks the new gap; then back-date past
   max(15m, interval) with the gap persisting -> the re-statement fires; assert no silence
   ever claimed over the unspoken gap. Row 16, reopened re-speak: PR appears -> spoken ->
   PR closes -> disappearance spoken -> SAME PR reopens -> spoken AGAIN (last-value law).
   Commit: `feat(emulation): rows 15-16, gap honesty and the reopened re-speak`
5. **Runner/README/plan wiring**: rows registered (16 total), emulation README matrix
   updated, the ambient plan's Workstream C section gains the deferral note verbatim from
   this plan's header, CHANGELOG (Added):
   `- The ambient behaviors are proven like everything else: pinned zero-network silence and request budgets in the suite, and four delta scenario rows in the emulation matrix (16 rows total).`
   Full gates + `python emulation/runner.py --offline --all` = 16/16. Commit:
   `docs: the magic is proven; conditional requests deferred with reasons`

## Completion
Stop after the last commit. Do NOT merge, push, or remove the worktree. Report: branch,
commits, gate exit codes, matrix output tail, files changed, deviations.
