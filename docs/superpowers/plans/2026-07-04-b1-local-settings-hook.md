# B1: The Reflex Hook Lives in Local Settings Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** The per-actor reflex hook is a knowing local opt-in, never a committed auto-run command: `install-hook` and onboard write it to `.claude/settings.local.json` (gitignored by Claude Code convention), existing installs in the committable `.claude/settings.json` are migrated out, and `status` reports the truth about where the hook lives. Closes the ambient plan rev 2's P0-4 latent leak (plan section Workstream B, binding).

**Why (recorded):** a hook entry in committed `.claude/settings.json` auto-runs on teammates' machines after clone, a documented supply-chain pattern. Config stays committed (inert data); the command never does.

**Branch:** worktree `git worktree add ../teamctx-b1 -b feat/local-settings-hook main`. Gates as separate commands with real exit codes; coverage >= 90 at the end.

**Pinned copy:**
- onboard hook step (wrote): unchanged shape, now naming the local path.
- migration step detail: `moved the reflex hook out of the committed .claude/settings.json into .claude/settings.local.json (a committed hook would auto-run on teammates' machines; the hook is a personal opt-in).`
- status, hook in the committed file: `the reflex hook is in the committed .claude/settings.json; re-run \`teamctx onboard\` to move it to .claude/settings.local.json (a committed hook auto-runs on teammates' machines).`
- ignore warning (when `.claude/settings.local.json` is NOT gitignored in this repo): `note: .claude/settings.local.json is not gitignored here; add it to .gitignore so the hook stays personal.`

### Task order (TDD per task, commit per task)
1. **Target change**: `cli.py` `install_hook_command` default and `install_hook_into_settings` callers, plus onboard's `_install_hook_step`, point at `root/.claude/settings.local.json`. All existing hook-install tests re-pointed; a new test asserts the committable `settings.json` is NOT touched on fresh install. Commit: `fix(hook-install): the reflex is personal; it installs to settings.local.json`
2. **Migration**: during onboard's hook step (never in dry-run), if the teamctx hook entry exists in `.claude/settings.json`, REMOVE exactly that entry (leave every other key byte-intact; atomic write; if the file becomes an empty object leave the empty object) and ensure it exists in `settings.local.json`; the step reports the pinned migration copy. Tests: migration with other settings present (untouched), with only our entry, idempotence (second run reports already), dry-run leaves both files alone. Commit: `fix(onboard): migrate the hook out of committed settings (supply-chain hygiene)`
3. **Status truth + ignore check**: `_hook_status_step` checks local first, then the committed file; a committed-file hit reports the pinned move copy (status "noted", never ok). After installing/migrating, onboard checks `git check-ignore .claude/settings.local.json`; not ignored -> append the pinned note to the hook step detail (never a failure; non-git trees skip the check). Tests for each state. Commit: `fix(status): the hook location is reported truthfully, with the move-it fix`
4. **CHANGELOG** (Fixed): `- The Claude Code reflex hook now installs to .claude/settings.local.json (personal, gitignored) instead of the committed settings file, and onboard migrates existing installs out; a committed hook would auto-run on teammates' machines.` Full gate + em-dash grep. Commit: `docs(changelog): hook is a personal opt-in`

## Completion
Stop after the last commit. Do NOT merge, push, or remove the worktree. Report: branch, commits, gate exit codes, files changed, deviations.
