# teamctx

Before you or your coding agent touch files, teamctx tells you what changed, what conflicts, what
failed, and what it could not verify, as source-backed evidence you can judge.

## Why

When you work through a coding agent, the expensive failures are not slow context gathering. They
are confident wrong context: the agent edits a file an open pull request is already changing, builds
on an acceptance criterion that moved, or proceeds on a "green" CI that is actually red. A wrong
answer delivered through a terminal you trust is worse than no answer.

teamctx keeps you and your agent pinned to the current, source-backed state of the systems your team
already uses. Its defining property is that there is no LLM in the content path. It normalizes,
routes, selects, and renders the record, and it never reinterprets what the record means. So facts
arrive faithful to the record, source-backed, and the same way every time. A green means checked, not guessed, and
where teamctx could not look, it says so plainly instead of implying all is well.

## What it checks

Run it before you start editing. From the systems of record your team already uses, teamctx surfaces:

- Open pull requests that touch the files you are about to change. Your own same-repo PR for the
  branch you are standing on is set aside with an FYI, never flagged against you (a fork PR still
  surfaces, on purpose).
- Checks that are failing on your branch, and checks that are still running (reported as
  unconfirmed, never assumed green).
- Acceptance criteria that changed on a linked issue since you started.
- Superseded docs: a doc in your change set that declares it was replaced by a newer one.

Live today: GitHub (open pull requests, check runs, and linked issues) and design docs declared in
your repository. The core is source-agnostic; GitHub is simply the first source wired up, with Jira
and GitLab next. teamctx reads metadata only (it does not read pull request bodies, comments, or
patches), speaks only to the structured slice it can actually verify, and does no broad search or
summaries. A source becomes supported only after it proves the same honest-coverage behavior.

## Install

teamctx is pre-release. Install from source:

```bash
git clone https://github.com/teamctx/teamctx
cd teamctx
pip install -e .
```

It needs read access to GitHub. If you use the GitHub CLI and are logged in (`gh auth login`),
teamctx picks that up automatically. Otherwise set a token in the environment (teamctx never stores
the value):

```bash
export GITHUB_TOKEN=ghp_...
# or point at a file instead:
export GITHUB_TOKEN_FILE=~/.config/teamctx/token
```

## Quickstart

```bash
# 1. One command sets it all up: detects the repo, writes a shareable .teamctx/config.json,
#    installs the Claude Code reflex hook, adds the CLAUDE.md snippet, and reports your
#    credential and a live reachability check. Idempotent; re-run any time. --dry-run previews.
teamctx onboard

# 2. Before you edit, see what changed around your files.
teamctx work-start --path src/auth/token.py
```

A clean start reads:

```
Looks clear to start.
  Checked: no other open PRs touch your files; no failing checks found.
  Not checked: spec changes (no issue is linked to this branch; link one to enable); docs (no docs root is configured; set work_start.docs_root to enable).
```

When something is in the way:

```
Before you start, here is what to handle first:
  • Open PR #7 changed src/auth/token.py: look at it before you edit so you don't undo each other's work (gh pr view 7 --repo acme/widgets)
  Also checked: no failing checks found.
  Not checked: spec changes (no issue is linked to this branch; link one to enable); docs (no docs root is configured; set work_start.docs_root to enable).
```

When the only overlapping PR is your own branch's PR, that is not a collision, and teamctx says so
instead of crying wolf:

```
Looks clear to start.
  Checked: no other open PRs touch your files; no failing checks found.
  FYI: Your own open PR #12 for this branch touches these files; not flagged as a collision.
  Not checked: spec changes (no issue is linked to this branch; link one to enable); docs (no docs root is configured; set work_start.docs_root to enable).
```

And when it could not verify something that matters, it says so rather than guessing:

```
Heads up: I can't confirm the important things yet:
  • Open PRs and failing checks: teamctx couldn't reach GitHub. Either it has no access yet (set GITHUB_TOKEN, or GITHUB_TOKEN_FILE with a path to a token file) or it's a temporary connection issue. Until it's back you won't see colliding PRs or red CI on your files.
  Not checked: spec changes (no issue is linked to this branch; link one to enable); docs (no docs root is configured; set work_start.docs_root to enable).
```

## Drill into a finding

To audit one finding (its full evidence, or how to open the source):

```bash
teamctx why pr:7 --path src/auth/token.py
teamctx open-source pr:7 --path src/auth/token.py
```

Selectors are the handles you see in the output: `pr:N`, `issue:#N`, `path:X`, `doc:PATH`, `gate:NAME`.

## Make it a reflex (Claude Code)

Grounding you do not run is worthless. `teamctx onboard` already installs an opt-in Claude Code
hook that runs the check automatically the first time you edit a file in a session, plus a one-line
CLAUDE.md instruction any agent can follow. If you only want the hook without the rest of onboard:

```bash
teamctx install-hook
```

The hook never blocks an edit. It just surfaces what is happening around the file you are about to
touch.

## The promise, stated honestly

- A green means checked, not guessed. teamctx never folds a coverage gap into a clear.
- Where it could not look (no access, a source down, or more results than it could enumerate), it
  returns Unknown, never a false all-clear.
- There is no LLM in the content path. teamctx is the reference for what is currently true in the
  record. It is not the judge of what the right call is (that is your job), and it does not claim to
  make the record itself correct (it delivers the record faithfully).

## What it is not

teamctx is deliberately bounded:

- No LLM and no agent runtime. It informs; it does not act or decide.
- No broad enterprise search, summaries, or fuzzy question answering.
- No productivity analytics and no presence tracking. It reads work artifacts and does not score or
  summarize people.
- It does not read private messages, pull request bodies, or patches, and it does not write to your
  source systems.

## How it works

Each connector reads approved metadata from a source and emits a typed, source-backed contract. A
deterministic core composes them, derives the findings, and returns one verdict per check with an
honest account of what it could and could not cover. The CLI output, the MCP tool result, and the
hook signal all derive from one broker answer and one shared classification; the hook says less on
purpose, but nothing it says can disagree with the full report. Replay the same inputs and you get
the same verdict every time.

Positioning and design: [design and positioning](docs/product/vision/reality-grounding-strategy-2026-06.md).
