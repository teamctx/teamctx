# S5b: Docs Relied-On Semantics Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** "Docs you rely on" means the team's declared docs set: with `docs_root` configured, ANY doc under it whose frontmatter declares `superseded_by` fires a "Verify before relying" card, regardless of which files the request touches. A configured, readable, clean scan is a real green. Spec: `docs/superpowers/specs/2026-07-03-autodiscovery-and-structure.md` section S5b (binding, revision 2); honesty pins P1-3 are law: `not_applicable` is NEVER mapped to clear; the docs connector stops emitting it; unreadable root and symlink-escape keep failing closed to UNKNOWN.

**Build AFTER S5a merges** (both touch contract_render/assessment tests). **Branch:** worktree `git worktree add ../teamctx-s5b -b feat/docs-relied-on main`. Gate per commit: the standard four commands. **One deviation from the spec's wording, decided by the CTO:** the README docs-bullet restore moves to S5c (all README edits in one slice, same phase, nothing ships between).

---

### Task 1: Flip the kind (one-entry change, the S6 payoff)

**Files:** `src/teamctx/core/kinds.py`; `tests/test_select.py` or the kinds tests.

- [ ] Failing test: a `doc_superseded` claim whose doc is NOT in the request paths refutes `no_superseded_docs` (same repo). Then: docs `CardKind.refutes_match` becomes `"repo-wide"`, and `_derive_doc_superseded_claim` drops the `doc not in request.paths` gate (keep the repo gate and the isinstance check). Update the pin-the-refactor test's expected refutes-match if it pins match modes. Full gate; commit `feat(docs): superseded docs refute repo-wide; reliance is the declared docs set`.

### Task 2: Connector stops emitting not_applicable

**Files:** `src/teamctx/connectors/docs.py`, `src/teamctx/connectors/docs_supersession.py`; their tests.

- [ ] `run_docs_supersession_probe` drops the `relied_on_doc_in_scope` computation; `normalize_superseded_docs` loses the parameter and always emits `fresh` for a completed scan (signals when superseded docs exist, none otherwise). Tests: clean scan asserts `fresh` + the render's real green ("the docs you rely on are current"); superseded-doc-outside-request-paths fires end to end (broker-level test); unreadable root and symlinked-escape tests unchanged (still unavailable/UNKNOWN). Remove the docs entry from the render's not-applicable overrides if it exists (the generic fallback remains for future kinds); `grep -rn "not_applicable" src/teamctx/connectors/` shows no emission.
- [ ] Full gate; commit `feat(docs): clean scan is a real green; not_applicable no longer emitted by docs`.

### Task 3: CHANGELOG + sweep

- [ ] CHANGELOG under Changed: `- The docs check now covers the whole declared docs folder: any doc there that names a newer replacement is flagged at work-start, whether or not you are editing it. A clean scan is a real green.` Full gate + coverage >= 90. Commit `docs(changelog): docs relied-on semantics`.

## Completion
Stop after the last commit. Do NOT merge, push, or remove the worktree. Report: branch, commits, gate tail, files changed, deviations. The CTO reviews and merges.
