# M1 — work_start as a reflex (Sprint 2, Slice A)

**Status:** design, awaiting CPO review · **Date:** 2026-06-27 · North star:
[reality-grounding](../../product/vision/reality-grounding-strategy-2026-06.md) (M1 = keystone)

## Purpose

Make `work_start` fire **at the moment work begins**, without the developer having to remember
it — so grounding-before-you-act becomes automatic, for the in-the-loop developer and the agent
alike. Two complementary mechanisms (Approach 3): a deterministic Claude Code hook, and a portable
instruction for any agent. The reflex is the keystone of the strategy: assurance you don't run is
worthless, and planting the "ground before you act" habit early is how the norm forms.

## Non-goals (sequenced elsewhere, not cut)

- **The shared CLI/MCP render voice pass** — bringing the *shared* render's verdict/UNKNOWN copy
  fully up to the surfaced-text principle for CLI and MCP is **M2, the immediate next slice**. M1
  renders its **own** concise hook signal (ready / heads up / can't-verify) for the inline
  injection; it does not reuse the full CLI report.
- **Per-file firing** — v1 is once per session. Per-file precision is a later enhancement.
- **A SessionStart variant** — possible complement, not v1.
- **Non-Claude-Code hooks** — other harnesses are covered by the portable instruction; native hooks
  for them are later.

## Design

### Mechanism (verified against the Claude Code hooks docs, 2026-06-27)

`PreToolUse` hook input (stdin JSON) includes `tool_name`, `tool_input.file_path` (for
Edit/Write/MultiEdit), `cwd`, and `session_id`. A hook injects context **without blocking** by
emitting `hookSpecificOutput.additionalContext` and **omitting** `permissionDecision`; the edit then
proceeds. This is teamctx's "informs, does not enforce" made literal — **the hook never blocks an
edit.**

### Component 1 — the hook (`teamctx-hook`)

A dedicated, lightweight console script (`teamctx-hook = teamctx.hook:main`, own module
`teamctx/hook.py`) — *not* a `cli.py` subcommand, so the hot no-op path stays cheap (see
Performance). On each Edit/Write/MultiEdit it:

1. Reads the PreToolUse JSON from stdin (stdlib only).
2. No-ops (emits nothing, exit 0) if: not a PreToolUse Edit/Write/MultiEdit, or no `file_path`, or
   **this session was already grounded** (once-per-session cache, keyed by `session_id` — a marker
   file under the OS temp dir, e.g. `…/teamctx-hook/<session_id>`). The cache check happens *before*
   importing the broker, so repeated edits cost only process start + a file stat.
3. Otherwise (first edit this session): marks the session grounded, then runs the existing
   `work_start` use case over the **in-flight change** — `paths` = the touched `file_path` plus the
   working-tree changed paths (`git -C <cwd> status --porcelain` / `diff --name-only`), deduped, so
   the collision check covers the whole change-set rather than only the triggering file (gate /
   criteria / docs are repo-wide regardless). `resolve_work_start_inputs(paths=<those>,
   root=Path(cwd), …)` → `render_work_start(...)`, with the token from the environment
   (`GITHUB_TOKEN` / `GITHUB_TOKEN_FILE`).
4. Renders a **concise signal** from the result (see Messaging — *ready* / *heads up* / *can't
   verify what matters*, not the full CLI report) and emits it as `additionalContext` (no
   `permissionDecision`), with a short lead that helps the agent relay it to its human.
5. **Fail-safe, always:** any error (not a git repo, network down, bad config) → exit 0, allow the
   edit, and emit a plain, decision-enabling message *or* nothing. Never a `permissionDecision`,
   never a crash, never a stack trace surfaced to the user.

Output JSON shape:
```json
{ "hookSpecificOutput": { "hookEventName": "PreToolUse", "additionalContext": "<plain text>" } }
```

### Component 2 — the portable instruction (the floor)

A documented snippet for the project's agent-instructions file (`CLAUDE.md` / `AGENTS.md`), printed
by `teamctx install-hook --print` and in the README:

> **Team context (teamctx).** Before you start editing files in this repo, run `teamctx work-start`
> and factor the result into your plan — it surfaces open PRs touching your files, failing checks,
> changed specs, and superseded docs. Tell your human collaborator anything relevant in plain terms
> so they can decide.

Works in any agent that reads an instructions file (the non-deterministic floor under the
deterministic hook).

### Component 3 — opt-in install (`teamctx install-hook`)

A `cli.py` subcommand (opt-in; nothing is ever installed automatically) that:
- Adds the `PreToolUse` → `teamctx-hook` entry to **project-local** `.claude/settings.json`,
  matching `Edit|Write|MultiEdit`. Idempotent (no duplicate entry on re-run); merges, never clobbers
  existing hooks.
- Prints the Component-2 instruction snippet for the user to paste into their `CLAUDE.md`.
- `--print` shows exactly what it would write and the snippet, **without writing anything**.

### Messaging — the surfaced-text principle, applied

Every string this hook surfaces is read by a human about to decide (directly or relayed by the
agent): plain, no internal jargon ("ground", "broker", a bare "UNKNOWN"), decision-enabling, and for
anything that couldn't run → **reason + how to turn it on + what to do if you won't/can't.** The
strategy's full statement is in [the surfaced-text principle](../../product/vision/reality-grounding-strategy-2026-06.md);
M2 brings the shared render up to it.

**The hook speaks in signals, not reports** (resolved in review). It maps the work_start result to
one of three glanceable signals, scaled to what the developer should do:

- **Ready** — the checks that matter came back clear: a clean go that *names what it checked* (so the
  claim is honestly scoped, not a bare "all clear"), with no "...but" hedge. Low-stakes coverage
  gaps (e.g. no linked issue → spec not checked) are **not** headlined; the one-time nudge to link an
  issue belongs at setup, not every edit.
  *e.g. "Looks clear to start on `src/api/orders.py` — no open PRs on these files, CI's green, docs current."*
- **Heads up** — something specific to handle first.
  *e.g. "Before you edit this: PR #42 already changes this file — worth a look (`gh pr view 42`)."*
- **Can't verify what matters** — a coverage gap that *changes the decision* (e.g. no GitHub access →
  collisions/CI unchecked): reason + how to fix + what you're missing. **Honest-UNKNOWN doesn't
  disappear** — a gap that matters becomes *this* signal; a gap that doesn't isn't headlined.

Exemplar — the hook can't reach GitHub (no token):

> teamctx couldn't check what else is happening around this file — it doesn't have access to GitHub
> yet. To switch that on, give it a token: run `teamctx install-hook` and it'll walk you through it.
> If you'd rather not connect it right now, that's fine — keep working; you just won't get a
> heads-up about open pull requests touching the same files, checks that are failing, or specs that
> changed since you started.

Exemplar lead line (relay steer) when there *is* something:

> Before you edit this file, here's what teamctx found in the team's current work — surface what
> matters to whoever you're working with:

### Performance (the hot path)

`teamctx-hook` runs on **every** Edit/Write/MultiEdit, but does real work only once per session. The
no-op path must stay cheap: read stdin, stat the session marker, exit — **before** importing
`work_start`/connectors/pydantic. Hence a dedicated lightweight module, not a `cli.py` subcommand
(which imports the whole broker at module load).

## Testing

- `tests/test_hook.py` (unit; stdin→stdout, no live session):
  - First Edit (temp git repo, stubbed fetchers / no token) → emits `additionalContext` JSON, exit 0.
  - Once-per-session: a second call with the same `session_id` no-ops (empty output) and does **not**
    re-run the broker.
  - Fail-safe: a broker/resolve error → exit 0, allow, plain message (or empty), never
    `permissionDecision`.
  - No token → the **can't-verify** signal: plain "couldn't check GitHub" guidance (reason + fix +
    fallback), never a false "ready".
  - Signal mapping: a clear result → **ready** (names the checks, no hedge); a collision/gate/spec/doc
    finding → **heads up** with the specific item; an important source unreachable → **can't verify**.
  - Non-Edit tool / missing `file_path` → no-op, exit 0.
- `tests/test_install_hook.py`: `install-hook` writes a valid, idempotent `.claude/settings.json`
  entry and merges with existing hooks; `--print` writes nothing.
- Existing suite stays green; ruff + mypy strict clean. Real-session behavior is exercised by the
  Sprint-2 multi-actor dogfood.

## To verify during implementation

- The exact `.claude/settings.json` hooks schema (matcher/command nesting) against the current Claude
  Code version before writing the install command.
- That `additionalContext` from a `PreToolUse` hook is delivered to the agent on the tool it fired
  for (sanity-check in a real session as part of the dogfood).

## Decisions (resolved in review, 2026-06-27)

1. **Speak in signals, not reports.** The hook output is one of *ready* / *heads up* / *can't verify
   what matters*. **Ready** is a clean go that names what it checked, with no "...but" hedge;
   low-stakes coverage gaps are not headlined. Honest-UNKNOWN surfaces only when it changes the
   decision (the *can't-verify* signal). See Messaging.
2. **Dedicated `teamctx-hook` console script** (not a `cli.py` subcommand) — keeps the per-edit
   no-op hot path cheap.
