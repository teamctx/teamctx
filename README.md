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

- Open pull requests or merge requests that touch the files you are about to change. Your own
  same-repo PR or MR for the branch you are standing on is set aside with an FYI, never flagged
  against you (a fork PR still surfaces, on purpose).
- Checks and pipelines that are failing on your branch, along with ones that are still running,
  skipped, or canceled, each surfaced honestly as not yet confirmed green.
- Acceptance criteria that changed since you started, on a linked GitHub issue or a Jira issue.
  The issue and the start time are derived from your branch name (a Jira key like PROJ-123, or a
  GitHub issue number), commit trailers, and merge point when you don't name them, and the
  derivation is named in the output so you can judge it.
- Design docs you rely on that have been superseded: a doc under your declared docs folder that
  names a newer replacement, or a Confluence page marked with the teamctx.superseded_by property,
  whether or not you are editing it.

Live today, across four sources: GitHub and GitLab forges (open pull requests and merge requests,
plus check runs and pipelines), GitHub issues and Jira for acceptance criteria, and local docs
folders and Confluence spaces for superseded docs. This four-source behavior was exercised by a
live multi-actor emulation: one operator driving several actor roles, human-style and agent-style,
through real GitHub, GitLab, Jira, and Confluence, with the run and its evidence committed at
`docs/validation/team-emulation-2026-07-04/SUMMARY.md` (in the repository).
teamctx reads metadata only (it does not read pull request bodies, comments, or patches), speaks
only to the structured slice it can actually verify, and does no broad search or summaries. A source
becomes supported only after it proves the same honest-coverage behavior.

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

For a GitLab project, set a GitLab token the same way:

```bash
export GITLAB_TOKEN=glpat-...
# or point at a file instead:
export GITLAB_TOKEN_FILE=~/.config/teamctx/gitlab-token
```

For Jira and Confluence, teamctx uses Atlassian Cloud basic auth: your account email and an API
token. Both halves must be present, or the source reports itself unavailable and names the missing
half.

```bash
export ATLASSIAN_EMAIL=you@example.com
export ATLASSIAN_API_TOKEN=...
# or point the token at a file instead:
export ATLASSIAN_API_TOKEN_FILE=~/.config/teamctx/atlassian-token
```

Which sources teamctx checks lives in the committed `.teamctx/config.json`. `teamctx onboard`
writes the forge and docs folder for you; add the `jira` and `confluence` blocks to turn those
sources on:

```json
{
  "schema_version": "teamctx.project_config.v0",
  "work_start": {
    "repo": "acme/widgets",
    "forge": "github",
    "docs_root": "docs",
    "jira": { "base_url": "https://your-site.atlassian.net" },
    "confluence": { "base_url": "https://your-site.atlassian.net", "space_key": "ENG" }
  }
}
```

## Quickstart

```bash
# 1. One command sets it all up: detects the repo, writes a shareable .teamctx/config.json,
#    installs the Claude Code reflex hook, adds the CLAUDE.md snippet, and reports your
#    credential and a live reachability check. Idempotent; re-run any time. --dry-run previews.
teamctx onboard

# 2. That's it. From now on, team context appears by itself: before the first edit of each
#    Claude Code session and again whenever something changes while you work; agents get the
#    same answer over MCP. What appears at the start looks like
#    the samples below (from a branch named 42-fix-auth in a repo with a docs/ folder, so
#    all four checks fire). To reproduce them by hand:
teamctx work-start --path src/auth/token.py
```

A clean start reads:

```
Looks clear to start.
  Checked: no other open PRs touch your files; the linked issue's criteria are unchanged (issue #42 from your branch name); the docs you rely on are current; no failing checks found.
```

When something is in the way:

```
Before you start, here is what to handle first:
  • Open PR #7 changed src/auth/token.py: look at it before you edit so you don't undo each other's work (gh pr view 7 --repo acme/widgets)
  Also checked: the linked issue's criteria are unchanged (issue #42 from your branch name); the docs you rely on are current; no failing checks found.
```

When the only overlapping PR is your own branch's PR, that is not a collision, and teamctx says so
instead of crying wolf:

```
Looks clear to start.
  Checked: no other open PRs touch your files; the linked issue's criteria are unchanged (issue #42 from your branch name); the docs you rely on are current; no failing checks found.
  FYI: Your own open PR #12 for this branch touches these files; not flagged as a collision.
```

And when it could not verify something that matters, it says so rather than guessing. This
last sample is a different situation: a branch with no derivable issue, no docs folder
configured, and GitHub unreachable:

```
Heads up: I can't confirm the important things yet:
  • Open PRs and failing checks: teamctx couldn't reach GitHub. Either it has no access yet (set GITHUB_TOKEN, or GITHUB_TOKEN_FILE with a path to a token file) or it's a temporary connection issue. Until it's back you won't see colliding PRs or red CI on your files.
  Not checked: spec changes (no issue could be derived from your branch or commits; name one with --issue); docs (no docs root is configured; set work_start.docs_root to enable).
```

## Drill into a finding

To audit one finding (its full evidence, or how to open the source):

```bash
teamctx why pr:7 --path src/auth/token.py
teamctx open-source pr:7 --path src/auth/token.py
```

Selectors are the handles you see in the output: `pr:N`, `issue:#N`, `path:X`, `doc:PATH`, `gate:NAME`.

## It appears on its own

Team context is ambient by design: after onboard, nobody runs a command in daily use. The opt-in
Claude Code hook that onboard installs grounds the session before its first edit and then keeps
watch: it quietly re-checks at an interval and speaks again when something actually changed
("since you started: GitHub PR #7 appeared, touching src/auth/token.py"); a standing gap it
cannot verify is re-stated every so often rather than forgotten. Silence means checked and
unchanged within the interval. The CLAUDE.md instruction onboard writes tells any
agent how to receive and use what appears (with a fallback for environments that do not run
hooks). If you only want the hook without the rest of onboard:

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

## How the claims are proven

Two layers back the behavior above. An offline emulation harness (`emulation/`) drives the real
CLI, hook, and MCP tool through a 22-row scenario matrix against bundled mock GitHub, GitLab,
Jira, and Confluence servers; anyone can run it with `python emulation/runner.py --offline --all`,
and each expected block quotes the real renderer. On top of that, a live multi-actor run against
real GitHub, GitLab, Jira, and Confluence is committed as evidence at
`docs/validation/team-emulation-2026-07-04/SUMMARY.md` (in the repository),
including the two residuals it left open.

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

Positioning and design: `docs/product/vision/reality-grounding-strategy-2026-06.md` (in the repository).
