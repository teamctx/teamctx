# teamctx: a short guide

teamctx watches the systems your team already uses and tells you, right in your Claude
Code session, when something moved around the work: an open PR touching your file, CI
failing on your branch, acceptance criteria that changed, a doc that was replaced. It is
read-only and there is no AI in the middle: it reports exactly what the record says, and
where it could not look, it says so.

## Set up

```bash
pip install teamctx
cd your-repo
teamctx onboard
```

That is the last command you run. If you are logged in to the `gh` CLI you are done;
otherwise set `GITHUB_TOKEN` (GitLab: `GITLAB_TOKEN`). Commit the `.teamctx/config.json`
it writes so your teammates inherit the setup.

## Use

Nothing to run. Context appears before your first edit and again when something changes:

```
since you started: GitHub PR #7 appeared, touching src/auth/token.py
```

Silence means checked and unchanged. Want it on demand?
`teamctx work-start --path <file>`.

## Team checks

Your team decides what runs. The committed `.teamctx/config.json` can enable or disable checks for everyone at once, and can declare simple record files (a deprecation list, a freeze calendar) that teamctx will surface like any other check. Nothing takes effect until the config is committed, and the output always names anything your team turned off.

## Two habits that make it sharper

- Put the issue ref in your branch name (`42-fix-login`, `PROJ-123-rollout`) or in a
  commit message (`Fixes #42`). That is how teamctx finds your linked issue.
- When a doc is replaced, add `superseded_by: <new-doc>` to the old file's frontmatter
  instead of deleting it. People building on the old version get told.

## If something looks off

Run `teamctx status`. It says what is set up and what is missing, with the fix. The hook
never blocks an edit; if teamctx errors, you get nothing rather than noise. To remove it,
delete the teamctx entry from `.claude/settings.local.json`.
