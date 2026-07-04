# A-2b: The Delta Voice Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** When reality changes mid-session, teamctx says exactly the change ("since you started: Open PR #7 appeared, touching src/auth/token.py") instead of re-speaking the whole report, and the session's first prompt becomes a grounding moment. Completes Workstream A.

**Architecture:** BINDING design: `docs/superpowers/specs/2026-07-04-ambient-delta-engine.md` REVISION 2 sections 4 and 5 (the deltas lane with NO new CardKind; kind never changes from deltas; a fresh-appearance delta SUPPRESSES the steady finding bullet for that item; deltas emit independent of the ready-guard; last-value dedup; UserPromptSubmit with file-path-free copy; emit `hookEventName` per event). Builds on the merged A-2a baseline engine.

**Branch:** worktree `git worktree add ../teamctx-a2b -b feat/delta-voice main`. Gates as separate commands with real exit codes; the offline matrix 12/12; coverage >= 90.

**Pinned copy (verbatim; the CTO owns every string):**
- appear, conflict: `since you started: {source_display} appeared, touching {paths}`
- appear, gate: `since you started: check '{gate}' started failing on this branch`
- appear, criteria: `since you started: {source_display} changed: {detail}`
- appear, docs: `since you started: {doc} was superseded by {superseded_by}` (no replacement named: `since you started: {doc} was superseded`)
- disappear, conflict: `since you started: {source_display} no longer touches your files`
- disappear, gate: `since you started: check '{gate}' is green again`
- disappear, criteria: `since you started: {source_display} is no longer flagged`
- disappear, docs: `since you started: the note about {doc} cleared`
- recovery (gap closed): `{source name} is back: ` followed by the check's normal clear phrase or its current finding line
- coverage-shrank: `since you started: {check phrase} can no longer be verified ({note})`
- UserPromptSubmit variants (file-path-free, spec-pinned): heads-up lead `teamctx: before you start, from the team's current work:` and ready line `teamctx: looks clear to start ({clear phrases}).`

### Task order (TDD per task, commit per task)
1. **Baseline schema v2 with delta material** (`ambient.py`): the stored value gains
   per-check (status, finding identities: PR/MR source_display+number+overlap paths, issue
   refs, gate names, doc names; NEVER evidence prose beyond source_display). Bump the state
   schema version; v1 files read as no-baseline (the existing corrupt-is-NONE path covers
   it; test exactly the version bump). A pure extractor builds the material from a
   BrokerAnswer. Commit: `feat(ambient): baselines carry the delta material (schema v2)`
2. **Delta computation** (pure function beside the extractor): old vs new material per
   check -> Delta records (direction appear/disappear/transition/coverage_shrank, check,
   identity, note). Last-value semantics by construction. Tests: every direction per check,
   the reopened-PR re-speak, identity matching across runs. Commit:
   `feat(ambient): the delta diff (what changed since the baseline)`
3. **Minting + the split ground path**: `work_start.py` gains
   `ground_work_start(inputs, observed_at, project_root) -> (request, documents)` (the
   existing answer functions delegate to it; no behavior change). The hook grounds once,
   diffs vs baseline, and when deltas exist appends an edge-built delta document
   (`changed_since_start` signals; scope carries check/direction/identity/note; reason codes
   `delta.{check}.{direction}`) and composes the SAME documents again (no second network).
   Commit: `feat(hook): deltas minted at the edge, composed through the one broker`
4. **The assess lane + speech**: `WorkStartAssessment` gains `deltas`; kind computation
   ignores them (kind is the current world). `hook_signal` and `contract_render` speak
   deltas FIRST with the pinned copy; a fresh-appearance delta suppresses the steady bullet
   for the same identity; delta speech bypasses the ready-guard empty-string path (a lone
   disappearance speaks over a quiet world). Tests: the P1-5 trio, one per pinned copy
   string, CLI/MCP untouched when no delta document exists. Commit:
   `feat(voice): the delta is spoken first, once, in one voice`
5. **UserPromptSubmit**: hook accepts the event (fields: session_id, cwd; no tool_name/
   file_path), grounds with the dirty-tree path set (possibly empty: A-1 semantics make
   that honest), emits with `hookEventName: "UserPromptSubmit"`, uses the pinned
   file-path-free copy variants. The PreToolUse path keeps its current copy. Tests: event
   parsing, empty-tree grounding (conflict not-applicable, gate still real per A-1), emit
   field correctness, the copy variants. Commit:
   `feat(hook): the session's first prompt is a grounding moment`
6. **CHANGELOG** (Added):
   `- Mid-session changes are spoken as exactly the change ("since you started: ..."), once, and the session's first prompt now grounds the work before any edit.`
   Full gate + em-dash grep + matrix 12/12. Commit: `docs(changelog): the delta voice`

## Completion
Stop after the last commit. Do NOT merge, push, or remove the worktree. Report: branch,
commits, gate exit codes, matrix status, files changed, deviations.
