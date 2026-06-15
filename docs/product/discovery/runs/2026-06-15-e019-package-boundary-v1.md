# E-019 Run: Package Boundary V1

Date: 2026-06-15

Purpose: answer whether the hybrid should be TeamCtx plus another package, and
what role the Ambara work should play.

## Honest Recommendation

Yes: use two implementation layers.

No: do not make them two products.

The product is TeamCtx. The durable/backend layer is part of TeamCtx's machinery.
It can be packaged separately for engineering reasons, but it should not ask for
separate user understanding.

## Proposed Boundary

| Layer | Working name | User sees it? | Owns | Does not own |
| --- | --- | --- | --- | --- |
| Product surface | `teamctx` | yes | CLI, agent-terminal rendering, setup, actions, source settings, context commands | durable signal normalization internals |
| Durable core | `teamctx-core` | no, except logs/debug | source signal contract, safety policy, source status, guidance records, rendering inputs, storage adapters | product copy, onboarding, user-facing nouns |

## Why Not Keep `ambara` As The Backend Brand?

Ambara has good engineering DNA, but as a product name it pulls us back toward a
separate memory/trust system.

That is exactly what we just learned not to build.

The durable layer should inherit Ambara's best ideas:

- reviewed guidance,
- quarantine/safety posture,
- stale-source fail-closed behavior,
- authority separation,
- source evidence lineage,
- active context without automatic authority.

But the product should not say: install Ambara, then TeamCtx uses it.

The product should say: install TeamCtx.

## Package Shape

### `teamctx`

Responsibilities:

- Agent terminal integration.
- `Working context` rendering.
- `Show why` surface.
- Setup for work sources.
- Session actions: `Use in this session`, `Hide for this session`, `Open source`.
- Drafting guidance from repeated or explicit source signals.
- Source status/settings UI or CLI.
- Product language and defaults.

### `teamctx-core`

Responsibilities:

- Source connector interfaces.
- Source-signal normalization.
- Safety and access policy.
- Stale/unavailable/blocked source handling.
- Guidance record lifecycle.
- Session context selection.
- Data storage adapters.
- Renderer input contract.
- Auditability for `Show why`.

### Optional Later Packages

Only after core value is proven:

- `teamctx-github`
- `teamctx-gitlab`
- `teamctx-jira`
- `teamctx-confluence`
- `teamctx-notes`

Do not split connectors early unless dependency or credential boundaries force
it.

## Import Direction

`teamctx` depends on `teamctx-core`.

`teamctx-core` does not depend on `teamctx`.

No user should need to install `teamctx-core` directly for normal use.

## Storage Boundary

The durable core owns storage primitives, but product policy decides what is
worth storing.

Store:

- source signals,
- source statuses,
- reviewed guidance records,
- session context selections,
- minimal source lineage for explanation.

Do not store:

- all source documents,
- all chat history,
- private notes by default,
- full activity timelines,
- productivity analytics,
- broad search indexes as the first abstraction.

## Product Copy Boundary

Users should not see:

- source signal,
- normalized signal,
- advisory match,
- guidance record,
- durable core,
- promotion,
- quarantine,
- authority tier.

Users may see:

- Working context.
- Project guidance.
- Good to know.
- Needs attention.
- Verify before relying.
- Source unavailable.
- Show why.
- Use in this session.
- Draft guidance.

## What Ambara Becomes

Ambara becomes R&D input and possibly a migration source for implementation
patterns.

It does not remain a separate user-facing dependency.

If code is reused, it should be renamed or wrapped so the user model remains
TeamCtx.

## Architectural Bet

This split gives us the best of both ideas:

- TeamCtx keeps the clean product flavor: context appears where agents work.
- The durable core keeps the hard trust mechanics: source state, safety,
  authority, freshness, and explainability.

The combination is better than either alone only if the core stays invisible
until the user asks `Show why`.

## Failure Modes

- `teamctx-core` becomes a generic memory database.
- Users have to learn two products.
- Connector count becomes the roadmap.
- Reviewed guidance becomes too heavy for small teams.
- Notes/docs become authority by accident.
- Debug/audit language leaks into everyday UX.

## Decision

Proceed with one product and two engineering layers:

- public product/package: `teamctx`,
- internal or dependency package: `teamctx-core`.

Do not pursue `ambara` as a standalone product in the new direction.

## Next Experiment

Sketch the first vertical prototype around one task:

- local workspace signal,
- GitHub/GitLab collision signal,
- issue changed-since-start signal,
- terminal `Working context` rendering,
- `Show why`,
- `Use in this session`.

This should happen before any broad connector planning.
