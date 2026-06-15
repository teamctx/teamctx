# E-003 Run: Local Source Probe V1

Date: 2026-06-15

Purpose: test whether local sources we already have can produce useful working
context without live integrations.

## Task Under Test

Continue TeamCtx product discovery after the Ambara pivot.

## Source Probe 1: Local Git State

Source family: code and review / local repo state
Source item: `git status --short` for TeamCtx
Selector: current repo
Permission proof: local workspace access
Freshness: current command output

Potential card:

```text
Needs attention
This repo already has unrelated edits.

Why this matters: discovery work should not overwrite README.md,
docs/engineering/build-plan.md, or docs/engineering/implementation-plan.md.
Source: local git status

Actions: Keep separate | Show changed files
```

Score: helped

Why: prevents accidental overwrite and keeps the discovery lane clean.

Failure mode: too much git noise if every dirty file becomes a card.

Decision: local dirty-tree context is high signal only when the task will edit
nearby files or create product docs.

## Source Probe 2: Existing TeamCtx Product Docs

Source family: docs and process / repo Markdown
Source item: `docs/product/product-plan.md`
Selector: product discovery task references TeamCtx direction
Permission proof: local repo file
Freshness: current workspace file

Potential card:

```text
Good to know
The existing product plan defines strong source boundaries but still reads like
an architecture-led product.

Why this matters: the current task is to prove the product experience before
building more machinery.
Source: docs/product/product-plan.md

Actions: Use as background | Open doc | Ignore
```

Score: maybe

Why: useful for CTO continuity, but too meta for an everyday product user.

Failure mode: product docs become a second brain dump instead of task-changing
context.

Decision: repo docs are useful for discovery sessions, but normal users should
only see doc-derived cards when they change what to do now.

## Source Probe 3: Ambara Source Provider Docs

Source family: R&D source / repo Markdown
Source item: Ambara `docs/source-providers.md`
Selector: current task asks which sources TeamCtx should pull from
Permission proof: local sibling repo file
Freshness: current workspace file

Potential card:

```text
Good to know
Ambara already proved a source-provider contract for GitHub, GitLab, Jira,
fixtures, and fixture-backed Linear/Confluence.

Why this matters: TeamCtx can reuse lessons, but should not inherit Ambara's
product language.
Source: Ambara docs/source-providers.md

Actions: Use as background | Open doc | Ignore
```

Score: helped

Why: prevents re-litigating known implementation facts while preserving the
product pivot.

Failure mode: pulls Ambara back into product surface instead of R&D input.

Decision: R&D docs can be high signal for internal product/engineering sessions,
but should not appear in ordinary customer agent work unless explicitly scoped.

## Source Probe 4: Ambara Obsidian Import Code

Source family: vault notes / prior implementation
Source item: Ambara `import_context.py` Obsidian planner and tests
Selector: current task asks whether Obsidian-like sources belong
Permission proof: local sibling repo file
Freshness: current workspace file

Potential card:

```text
Good to know
Obsidian support exists as reviewed import logic, not live context lookup.

Why this matters: the product can test vault notes without claiming live
Obsidian connector support.
Source: Ambara import_context.py and tests

Actions: Use as background | Open tests | Ignore
```

Score: helped

Why: clarifies the current capability boundary.

Failure mode: user hears "Obsidian support" and assumes broad vault ingestion.

Decision: Obsidian should enter discovery as allowlisted vault/folder notes,
not as "connect your whole vault."

## Early CTO Read

Local source probes are useful for us as builders, but many are too meta for end
users. That is a distinction the product needs:

- Builder/product sessions can use repo docs, dirty-tree state, and R&D notes.
- Everyday agent sessions should mostly get task-changing cards from work
  artifacts, not broad documentation context.
- Source cards need a stronger action model than `Use as background`.

Action language still unresolved:

- `Use now` is vague.
- `Use as background` is honest but weak.
- `Open source` is clear but not enough.
- `Pin for this session` may be better for ephemeral context.
- `Draft guidance` may be better than `Save for later` for future context.

## Decision

Revise language before connector work. Continue probing sources manually.
