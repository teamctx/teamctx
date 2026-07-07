# teamctx user guide

This is the guide to hand a teammate. It covers what teamctx does, how to install and set it
up, what appears while you work, how to label things so the checks can see them, and what to
do when something reads wrong.

## What it does

Before you or your coding agent edit a file, teamctx checks the systems your team already
uses and surfaces what moved around the work:

1. **Colliding pull and merge requests.** Someone else has an open PR or MR touching a file
   you are about to edit. Your own PR for your current branch is set aside as an FYI, never
   an alarm.
2. **Failing or unconfirmed CI on your branch.** Failing checks are named. A run still in
   progress is reported as unconfirmed, never counted as green.
3. **Acceptance criteria that moved.** If your branch or commits link an issue, teamctx
   tells you when that issue's criteria changed since you started.
4. **Superseded docs.** A doc in your docs folder, or a Confluence page, that names a newer
   version surfaces before you build on the old one.

Two properties matter for how you read it. There is no language model between the record and
you: teamctx routes and renders what the source systems say, so the same inputs give the same
result every time. And it is honest about coverage: anywhere it could not look, it says so on
its own line, with how to fix it. A gap is never folded into a clear result. Silence, once
you are set up, means checked and unchanged, within the re-check interval.

teamctx is read-only. It reads metadata (titles, file lists, statuses, timestamps), not PR
bodies, comments, patches, or private messages, and it never writes to your source systems.

## Install

teamctx is pre-release: install from source. You need Python 3.12+ and git.

```bash
git clone https://github.com/teamctx/teamctx
cd teamctx
pip install -e .
```

For agents over MCP, install the extra: `pip install -e '.[mcp]'`.

## Set up a repository (once per repo)

From the repo you work in:

```bash
teamctx onboard
```

This detects the repo and forge from your git remote, writes a shareable
`.teamctx/config.json`, installs the Claude Code hook into your personal
`.claude/settings.local.json` (gitignored, opt-in, yours), adds a team-context section to
`CLAUDE.md` so agents know how to use what appears, and prints a line per step with what it
found. `--dry-run` shows everything without writing; `--force` overwrites an existing
config.

The config is meant to be committed, so one person onboards and everyone after them
inherits the source setup. Credentials are never in the config; each person supplies their
own through the environment:

- **GitHub:** `GITHUB_TOKEN` (or `GITHUB_TOKEN_FILE` pointing at a file). If you use the
  `gh` CLI and are logged in, teamctx uses that automatically.
- **GitLab:** `GITLAB_TOKEN` (or `GITLAB_TOKEN_FILE`). A personal access token with
  `read_api` scope.
- **Jira and Confluence:** `ATLASSIAN_EMAIL` plus `ATLASSIAN_API_TOKEN` (or
  `ATLASSIAN_API_TOKEN_FILE`). Create the token at id.atlassian.com under Security.

Check yourself anytime:

```bash
teamctx status
```

It reports the config, the hook, the CLAUDE.md section, and which credentials are visible,
with a next step if something is missing.

### Jira and Confluence (optional, per repo)

If your team tracks work in Jira or documents in Confluence, add the blocks to
`.teamctx/config.json`:

```json
{
  "schema_version": "teamctx.project_config.v0",
  "work_start": {
    "repo": "acme/widgets",
    "forge": "github",
    "docs_root": "docs/",
    "jira": { "base_url": "https://your-site.atlassian.net" },
    "confluence": { "base_url": "https://your-site.atlassian.net", "space_key": "ENG" }
  }
}
```

`docs_root` turns on the local docs check; the Jira block lets issue keys like `PROJ-123`
resolve; the Confluence block scans one space for superseded pages.

## Daily use

There is none. That is the point. After onboard, team context appears by itself in a Claude
Code session: once before the session's first edit (or at your first prompt), and again
whenever something relevant changes while you work. It looks like this:

```
Before you start, here is what to handle first:
  • Open PR #7 changed src/auth/token.py: look at it before you edit so you
    don't undo each other's work (gh pr view 7 --repo acme/widgets)
```

and mid-session, when the world moves, exactly the change:

```
since you started: GitHub PR #7 appeared, touching src/auth/token.py
```

The hook never blocks an edit and never breaks your session; if teamctx errors, you simply
get nothing. It quietly re-checks at an interval (default 90 seconds, tune with
`TEAMCTX_AMBIENT_INTERVAL_SECONDS`, floor 30) and speaks only when the answer changed, so
you are not re-told what you already know. A standing gap it cannot verify is re-stated
every so often rather than forgotten.

To get the same answer on demand, in any terminal:

```bash
teamctx work-start --path src/auth/token.py
```

Useful flags: repeat `--path` for several files; `--issue PROJ-123` or `--issue '#42'` to
name the linked issue explicitly; `--since 2026-07-01T00:00:00Z` to ask about issue changes
after a point in time; `--branch`, `--docs-root`, and `--github-repo` to override detection.

To drill into one finding:

```bash
teamctx why pr:7        # how this finding was derived, from what evidence
teamctx open-source pr:7  # print the URL of the original record
```

Selectors: `pr:N`, `issue:REF`, `path:X`, `doc:PATH`, `gate:NAME`.

### Agents over MCP

`teamctx-mcp` serves the same check as a `work_start` tool. Point it at the repo with
`TEAMCTX_PROJECT_ROOT` and give the server process the credentials; agents calling the tool
never see them. The CLAUDE.md section onboard writes tells agents to factor what appears
into their plan and to relay anything relevant to you in plain terms.

## How to label things

teamctx reads what your team already produces. Three habits make the checks sharper.

**Link the issue you are working on.** teamctx derives the linked issue from your branch
name or recent commits, and it always names how it derived it so you can judge. Any of
these work:

- A branch containing the issue ref: `42-fix-token-refresh`, `feature/PROJ-123-rollout`.
- A commit trailer: `Fixes #42`, `Closes PROJ-123`, `Resolves #42` (case-insensitive).
- Explicit override when neither applies: `--issue '#42'`.

**Mark superseded local docs.** When a design doc is replaced, add one line to the OLD
file's frontmatter instead of deleting it:

```markdown
---
superseded_by: docs/design/auth-v2.md
---
```

Anyone who edits code that relies on the old doc then sees "was superseded by
auth-v2.md" before they build on it.

**Mark superseded Confluence pages.** Same idea, as a content property on the OLD page:
key `teamctx.superseded_by`, value the replacement page's title or URL. (Page properties
live under the page's three-dot menu, or set it via the API.)

## Reading the output

- **"Looks clear to start."** followed by a `Checked:` list. Every item on that list is
  something teamctx actually looked at just now. Clear means checked, not guessed.
- **"Before you start, here is what to handle first:"** findings, each with the action and
  the exact command to open the original record.
- **"Heads up: I can't confirm the important things yet:"** coverage gaps, each with the
  reason and the fix (usually a missing credential). This is the normal first-run
  experience before credentials are set.
- **"Couldn't fully check"** means a source answered but something (for example a paused
  CI pipeline) kept the answer from being complete; teamctx tells you which part.
- **FYI lines** are context that is not an alarm, like your own open PR for this branch.

When in doubt, trust the itemization over your assumption: if a check is not on the
`Checked:` list, it was not checked, and the output will say why.

## Troubleshooting

- **Nothing ever appears.** Run `teamctx status` in the repo. It will tell you if the
  config, hook, or credentials are missing and what to do.
- **"couldn't reach GitHub" (or GitLab/Jira/Confluence).** Your credential is missing,
  expired, or lacks scope. The message names the variable to set.
- **The issue check says "no linked issue found."** Your branch name and commits carry no
  issue ref; use the naming habits above or pass `--issue`.
- **You want it quieter or louder.** `TEAMCTX_AMBIENT_INTERVAL_SECONDS` sets the re-check
  interval (default 90, floor 30).
- **You want the hook gone.** Delete the teamctx entry from
  `.claude/settings.local.json`. It was only ever installed in your personal file.

## What teamctx will not do

It will not push, comment, label, or write anything to your source systems. It will not
read message bodies or diffs. It will not answer from a language model. And it will not
tell you a clear it did not verify: where it could not look, it says so. What you do with
what it surfaces stays your call.
