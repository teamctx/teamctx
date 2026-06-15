# Relevance Noise Boundary V1

Date: 2026-06-15

Status: discovery draft

## Decision

A stale, unavailable, or blocked source can produce working context only when it
changes confidence for the current task scope.

Source health is part of context, but it is not a standing warning banner.

## What Changed

The auth-token fixture still contains the stale release checklist card, but the
card is marked:

```json
{
  "default_agent_visible": false,
  "relevance": "release_task_only",
  "why_hidden_by_default": "The current task is not release-scoped."
}
```

Default auth-token context now renders only:

- Git host collision.
- Issue changed since branch start.
- Reviewed project guidance.

The stale release checklist has its own golden output:

- `fixtures/vertical-slice/golden/context-release-stale-source.txt`

## Product Rule

Render source-health caveats when all are true:

1. The source is configured for the project or task.
2. The source family is relevant to the current task scope.
3. The source health state changes what the agent should assume.
4. The caveat can be stated without exposing private or inaccessible details.

Do not render source-health caveats when they merely say that some unrelated
configured source is stale.

## Examples

Render:

```text
Prepare release checklist updates for today's auth-service release.
```

Do not render by default:

```text
Update src/auth/token.py to add token rotation retry handling for API-482.
```

## Why This Matters

The product fails if every configured source can interrupt every task.

The right behavior is not maximum safety copy. It is scoped uncertainty that
changes the next action.

## Implementation Implication

The renderer needs relevance gates, not just visibility gates:

- `policy.can_render_to_agent` says a card is allowed.
- `default_agent_visible` says whether it appears without explicit action.
- `relevance` says when it applies to the current task.

A card can be safe to render and still irrelevant.
