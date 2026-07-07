# teamctx in five minutes

Before you or your coding agent edit a file, teamctx shows what moved around the work:
an open PR touching the same file, CI that is failing or still running, acceptance
criteria that changed on the linked issue, a design doc that was replaced. It is
read-only, it surfaces and stores metadata only (titles, file lists, statuses), and there
is no language model in the path: the same inputs give the same result every time. Where
it could not look, it says so and how to fix it. A gap is never dressed up as a clear.

## Set up (once per repo, about two minutes)

```bash
pip install teamctx
export GITHUB_TOKEN=...   # or be logged in to the gh CLI; that works automatically
cd your-repo
teamctx onboard
```

That is the last command you run. `onboard` detects the repo, writes a shareable
`.teamctx/config.json` (commit it; teammates who onboard after you inherit it), installs
the pre-edit hook into your personal `.claude/settings.local.json`, and adds a short
section to `CLAUDE.md` so agents know what to do with what appears.

On GitLab, set `GITLAB_TOKEN` (a personal access token with `read_api`) instead. For
Jira or Confluence, set `ATLASSIAN_EMAIL` and `ATLASSIAN_API_TOKEN` and add your site to
the config; `teamctx status` will show you where things stand at any time.

## Use

There is nothing to run. Team context appears in your Claude Code session before the
first edit, quietly re-checks while you work, and speaks again only when something
actually changed:

```
since you started: GitHub PR #7 appeared, touching src/auth/token.py
```

Silence means checked and unchanged. If teamctx cannot verify something (no token yet,
GitHub unreachable), it says exactly that instead of staying quiet.

Want the answer right now, or outside a session? `teamctx work-start --path <file>`
prints the same check in full (this is also the one that checks Confluence pages).
Agents get the same answer through the `work_start` MCP tool via `teamctx-mcp`.

## Label things so the checks can see them

- **Put the issue ref in your branch name** (`42-fix-token-refresh`,
  `feature/PROJ-123-rollout`) or in a commit trailer (`Fixes #42`, `Closes PROJ-123`).
  That is how the criteria check finds the issue; it works for GitHub issues and Jira.
- **When a doc is replaced, mark the old one** instead of deleting it. Local markdown:
  add `superseded_by: docs/design/auth-v2.md` to its frontmatter. Confluence: set the
  content property `teamctx.superseded_by` on the old page. Anyone building on the old
  version gets told before they start.

## If something reads wrong

`teamctx status` tells you what is configured, what is installed, and whether your forge
credential is visible, with a next step for anything missing. The hook never blocks an
edit and never breaks a session: if teamctx errors, you get nothing rather than noise.
To remove it, delete the teamctx entry from `.claude/settings.local.json`; it only ever
lived in your personal file.
