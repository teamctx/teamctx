# E-048: Contract Terminal Vertical Slice

Date: 2026-06-16

## Question

Can a Core Contract V0 document become usable terminal context without falling
back to fixture-only rendering or connector-specific card logic?

## Method

Add file-backed Core Contract document helpers, terminal rendering for contract
cards, and CLI support for:

```bash
teamctx refresh
teamctx context --contract .teamctx/context.json
teamctx why <card-id> --contract .teamctx/context.json
teamctx open-source <card-or-source-id> --contract .teamctx/context.json
```

The existing fixture commands continue to work.

## Result

The terminal vertical slice now has a contract-backed path:

- `refresh` writes a Core Contract document from the GitHub PR metadata probe.
- `context --contract` renders working context plus relevant source status.
- `why --contract` explains source, reason, scope, freshness, confidence, source
  body state, and agent visibility.
- `open-source --contract` is read-only and does not invent source body text;
  status-only targets remain closed.

## Product Read

This is the first usable bridge from connector output to terminal context. The
user still does not need to know contract terminology; the contract file is the
internal handoff between refresh and terminal rendering.

## Remaining Gap

The flow still needs a real opted-in GitHub run and a cleaner local project config
so the CPO demo does not require long command flags.
