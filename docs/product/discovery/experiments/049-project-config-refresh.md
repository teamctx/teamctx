# E-049: Project Config Refresh

Date: 2026-06-16

## Question

Can the terminal vertical slice use a small local project config so the demo does
not require long command flags?

## Method

Add `teamctx.project_config.v0` with a narrow GitHub source config:

```json
{
  "schema_version": "teamctx.project_config.v0",
  "github": {
    "repo": "org/app",
    "token_env": "GITHUB_TOKEN",
    "include_title": false
  },
  "default_output": ".teamctx/context.json"
}
```

`teamctx refresh` now reads `.teamctx/config.json` by default. Flags can still
override config. The config stores the token environment variable name, not the
token value.

## Result

The demo command can now be:

```bash
teamctx refresh --path src/auth/token.py --task "Update token rotation"
teamctx context --contract .teamctx/context.json
teamctx why card_github_pr_482_collision --contract .teamctx/context.json
teamctx open-source card_github_pr_482_collision --contract .teamctx/context.json
```

If GitHub credentials are missing, refresh still writes a context document with
source status.

## Decision

Keep the config small for Sprint 01. Do not add multi-source config until the
first Git-host demo is solid.
