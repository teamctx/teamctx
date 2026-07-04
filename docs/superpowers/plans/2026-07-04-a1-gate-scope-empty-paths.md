# A-1: Branch-Scoped Gate + Empty-Path Honesty Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Two product fixes pinned by the delta-engine spec rev 2 section 5 (binding), valuable on their own: the gate check becomes branch-scoped by declaration (a red branch surfaces no matter which files the request names, including none), and a conflict check with an empty path set reads not-applicable, never clear.

**Why:** today `FailingGate.files` is set to the request paths, so the path-overlap derive always passes when paths exist (vestigial scoping) and never fires with empty paths: a genuinely red branch reads "no failing checks found" from a zero-path grounding. Same class as the S5b docs change.

**Branch:** worktree `git worktree add ../teamctx-a1 -b feat/gate-branch-scope main`. Gates as separate commands with real exit codes; coverage >= 90 at the end.

**Pinned copy:** the empty-path conflict note (verbatim): `no files in scope yet; open pull requests can't be compared until there are paths`.

### Task order (TDD per task, commit per task)
1. **Gate goes repo-wide**: in `core/kinds.py` the missed_gate kind flips to
   `refutes_match="repo-wide"`; `_derive_missed_gate_claim` drops the path-overlap gate
   (keeps the repo gate); `FailingGate` loses `files` (gate_status.py; the signal scope
   drops the `files` key); the claim subject for a gate card becomes the gate name (subject
   paths carry the gate name for identity, matching how criteria carries issue refs).
   Update the pin-the-refactor registry test and every gate fixture. Tests: a red branch
   fires while the request paths are unrelated files; a red branch fires with EMPTY paths
   (broker-level); a green branch stays clear; the render copy is unchanged.
   Commit: `feat(gate): a red branch surfaces regardless of the files in scope`
2. **Empty-path conflict honesty**: in `runner.py`, when the normalized path set is empty,
   skip the PR probe and emit a `not_applicable` git_hosting status with the pinned note
   (reuse the existing not-applicable machinery; closure reads not_applicable[out-of-scope];
   assessment maps to not_applicable; the render's Not applicable lane speaks the note via
   the coverage-note preference). Tests: empty paths -> conflict not_applicable with the
   pinned note text, never "no other open PRs touch your files"; non-empty paths unchanged;
   the e2e render line asserted.
   Commit: `fix(runner): an empty path set never clears the conflict check`
3. **CHANGELOG** (Changed + Fixed):
   `- The gate check is branch-scoped: failing checks and pipelines on your branch surface no matter which files you are editing.`
   `- A work-start with no files in scope reports the conflict check as not applicable instead of a false clear.`
   Full gate + em-dash grep. Commit: `docs(changelog): branch-scoped gate; empty-path honesty`

## Completion
Stop after the last commit. Do NOT merge, push, or remove the worktree. Report: branch, commits, gate exit codes, files changed, deviations.
