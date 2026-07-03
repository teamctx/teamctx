# S5c: Onboard Docs Detection + Truthful Snippet Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Onboard detects a conventional `docs/` folder and configures it; the CLAUDE.md snippet claims exactly what fires (all four checks, with the two conditional ones stating their conditions); README regains the full docs bullet and a four-check quickstart sample generated through the real pipeline. Spec: `docs/superpowers/specs/2026-07-03-autodiscovery-and-structure.md` section S5c (binding). **Build AFTER S5a and S5b merge.**

**Builder: Fable (copy-heavy); codex adversarially reviews the diff before merge.** Branch: `feat/onboard-docs-snippet` (main worktree is fine; Fable coordinates).

**Pinned copy:**
- New `CLAUDE_MD_SNIPPET` body (the old body joins `_KNOWN_BODIES` for migration):
  `## Team context (teamctx)` then: `Before you start editing files in this repo, run `teamctx work-start` and factor the result into your plan. It surfaces open pull requests touching your files, failing checks on your branch, acceptance criteria that changed when an issue is linked from your branch or commits, and superseded docs when a docs folder is configured. Tell your human collaborator anything relevant in plain terms so they can decide.`
- onboard docs step, found: `found a docs/ folder; superseded docs there will be flagged.`
- onboard docs step, not found: `no docs/ folder found; set work_start.docs_root in .teamctx/config.json to flag superseded docs.`
- README docs bullet: `- Design docs you rely on that have been superseded: any doc under your declared docs folder that names a newer replacement.`

### Tasks
1. **Onboard docs detection.** In `_config_step_and_effective_repo`'s write path only (existing configs untouched, spec pin): when writing a NEW config and `root/docs` is a directory containing at least one `*.md` (recursive), include `docs_root="docs"`; a new `StepResult("docs", ...)` reports the pinned copy either way (also in dry-run and existing-config runs, reporting what IS configured). `run_status` gains the same read-only docs line. TDD against `tests/test_onboard.py` + `tests/test_status.py` patterns.
2. **Snippet.** Replace `CLAUDE_MD_SNIPPET`; append the previous body to `_KNOWN_BODIES`; migration tests: a marked unedited OLD block upserts to the new one (`outdated` path); the S3 classifier tests get the new body as `current`.
3. **README.** Docs bullet restored (pinned above); quickstart sample regenerated through the real pipeline with all four checks firing (extend the sample-generation script with issues+docs inputs; paste its byte output); the criteria bullet mentions derivation ("when an issue is linked from your branch or commits").
4. **CHANGELOG** under Added: `- onboard detects a docs/ folder and configures it; the CLAUDE.md snippet now claims all four checks with their conditions stated.` Full gate + em-dash grep.

## Completion
Fable stops before merge; codex reviews the diff (claims-vs-code, byte-accuracy of the README sample, copy rules); merge on verdict.
