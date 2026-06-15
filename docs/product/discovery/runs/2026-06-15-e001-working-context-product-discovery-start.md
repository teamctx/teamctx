# E-001 Run: Product Discovery Start

Task: Begin TeamCtx product discovery and decide what to test before writing
more product code.

Scope: TeamCtx product direction, source strategy, user language, first
experiments, and Ambara primitives as R&D input.

Prepared: 2026-06-15

Note: This packet is an internal concierge artifact, not terminal command syntax.
No user is expected to type these section names or learn these labels. The point
is to evaluate what context would have helped before designing the actual product
surface.

## Heads Up

- Item: Existing TeamCtx docs are useful, but implementation-heavy.
  Reason: They define strong architecture and source boundaries, but the current
  decision is to prove the product shape before building more machinery.
  Source: `docs/product/product-plan.md`, discovery README, CPO direction.
  Action: Use existing docs as input, not as the active build plan.

- Item: Users should not need TeamCtx vocabulary.
  Reason: The CPO explicitly rejected product language that requires learning
  terms like promotion, ledger, registry, or memory.
  Source: product conversation.
  Action: Test only plain actions: `Use now`, `Keep for future`, `Ignore`,
  `Why am I seeing this?`

- Item: Source breadth is a trap.
  Reason: GitHub, GitLab, Jira, Linear, Confluence, Notion, Obsidian, Markdown,
  Slack, and Teams all sound valuable, but broad connectors can make the product
  feel like surveillance or enterprise search.
  Source: TeamCtx product docs and CPO source-strategy discussion.
  Action: Probe source families manually before investing in connectors.

- Item: The repo already has unrelated dirty work.
  Reason: `git status --short` shows modified `README.md`,
  `docs/engineering/build-plan.md`, and untracked
  `docs/engineering/implementation-plan.md`.
  Source: local git status.
  Action: Keep discovery work isolated under `docs/product/discovery/`.

## Saved Guidance

- Guidance: The product promise is working context, not memory.
  Applies when: naming surfaces, writing cards, deciding source behavior.
  Source: product conversation.
  Confidence: high.

- Guidance: Ambara is now R&D input, not the product plan.
  Applies when: deciding whether to reuse trust spine, source safety, reviewed
  guidance, or Obsidian import mechanics.
  Source: product conversation.
  Confidence: high.

- Guidance: Preserve only what reduces future interruption.
  Applies when: testing `Keep for future` or saved guidance.
  Source: product conversation and discovery README.
  Confidence: medium-high.

- Guidance: Chat must be explicit handoff only.
  Applies when: discussing Slack or Teams.
  Source: TeamCtx docs and CPO concerns about tracking.
  Confidence: high.

- Guidance: `Keep for future` is still unproven language.
  Applies when: designing E-002 cards and action tests.
  Source: CPO concern that users should not learn internal product terms.
  Confidence: medium.

## Source Health

- Source: Local TeamCtx docs.
  Status: available.
  Meaning: usable for discovery scaffolding and source-family assumptions.

- Source: Existing Ambara primitives.
  Status: available as prior R&D, not active product direction.
  Meaning: reuse selectively after product experiments identify a need.

- Source: Live workplace APIs.
  Status: not used.
  Meaning: no live connector support is being claimed in this run.

- Source: External model critique.
  Status: not run yet.
  Meaning: use the model critique template after the first packet or language
  examples exist.

## Not Used

- Source or item: Broad Slack, Teams, email, or DM history.
  Reason: outside the product boundary and likely to feel like monitoring.

- Source or item: Old Ambara build plan.
  Reason: superseded by TeamCtx product discovery.

- Source or item: Live GitHub, Jira, Confluence, Notion, or Obsidian data.
  Reason: first run is testing packet shape, not connector behavior.

## Open Questions

- Question: Is `Working context` the right visible name?
  Why it matters: If even the container label feels product-y or vague, every
  downstream card will carry that tax.

- Question: Does `Keep for future` feel helpful, permanent, or creepy?
  Why it matters: This is the user-facing replacement for internal promotion.

- Question: What is the minimum first source set for a real dogfood week?
  Why it matters: We need enough signal to test the thesis without turning the
  experiment into integration work.

- Question: Should saved guidance be team-level, repo-level, task-level, or all
  three?
  Why it matters: Scope is the difference between useful context and ambient
  noise.

## Keep For Future Candidate

- Candidate: "TeamCtx should be felt as working context, not learned as a new
  system."
  Why it may matter later: This is the clearest product boundary emerging from
  the pivot.
  Review needed: CPO should confirm whether this language feels right.

## After-Session Notes

- Helped:
- Distracted:
- Missing:
- Unsafe or uncomfortable:
- Decision:
