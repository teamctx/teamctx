# E-001 Run: Product Pivot Session

Date: 2026-06-15

## Task

Replace the Ambara-first build direction with TeamCtx product discovery and
start experiments to decide what the product should be.

## Scope

- TeamCtx product discovery.
- Existing Ambara work as R&D input, not the active product plan.
- Current repo docs under `agents/repos/teamctx`.
- Previously verified Ambara primitives: source providers, trust spine,
  Obsidian import, reviewed guidance mechanics.

## Working Context

### Heads Up

- The old Ambara build plan is superseded.
  Reason: CPO has decided Ambara is not the product path; it is an R&D asset.
  Source: product conversation on 2026-06-15.
  Action: Do not continue Ambara build-plan work unless a piece is pulled into
  a TeamCtx experiment.

- TeamCtx is promising but not yet defined enough to build as a product.
  Reason: current docs describe strong architecture and source boundaries, but
  the user-facing product language and workflow still need proof.
  Source: `docs/product/product-plan.md` and product conversation.
  Action: prioritize discovery experiments over implementation.

- Existing TeamCtx repo has uncommitted work.
  Reason: `git status --short` shows modified `README.md`,
  `docs/engineering/build-plan.md`, and untracked
  `docs/engineering/implementation-plan.md`.
  Source: local git status.
  Action: add discovery docs separately; do not overwrite existing edits.

### Saved Guidance

- Everyday users should not need to know internal nouns.
  Applies when: designing CLI, MCP output, docs, or card actions.
  Source: product conversation.
  Confidence: high.

- The product should appear as working context, not as a new place to manage.
  Applies when: choosing surfaces and onboarding.
  Source: product conversation.
  Confidence: high.

- Source text is evidence, not instruction.
  Applies when: consuming PRs, issues, docs, notes, or chat handoffs.
  Source: Ambara trust-spine work and TeamCtx docs.
  Confidence: high.

### Source Health

- Local TeamCtx docs: available.
  Meaning: safe to use for discovery scaffolding.

- Live external product APIs: not used in this run.
  Meaning: no connector behavior is being claimed.

- Ambara Obsidian support: import-oriented, not a live TeamCtx connector.
  Meaning: reuse the learning, but do not claim live Obsidian source support yet.

### Not Used

- Slack/Teams broad chat history.
  Reason: explicitly outside product boundary; too surveillance-shaped.

- Ambara brand as product surface.
  Reason: current product direction makes Ambara an internal/R&D source of
  mechanics.

## After-Session Notes

Pending.
