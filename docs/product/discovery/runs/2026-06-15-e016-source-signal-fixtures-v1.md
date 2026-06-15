# E-016 Run: Source Signal Fixtures V1

Date: 2026-06-15

Purpose: create the first concrete source-signal fixture pack.

## Created Artifacts

- `templates/source-signal-fixture.md`
- `fixtures/source-signals/v1.md`

## Fixture Coverage

| Fixture | Source family | Signal | Decision |
| --- | --- | --- | --- |
| 1 | Local workspace | `changed_since_start` | launch-ready |
| 2 | Git hosting | `collision` | launch-ready |
| 3 | Issue tracker | `changed_since_start` | launch-ready |
| 4 | Configured docs | `stale_source` | launch-ready |
| 5 | Linked docs | `unavailable_source` | launch-ready |
| 6 | Approved local notes | `approved_guidance` advisory | probe |
| 7 | CI/deploy | `runtime_state` | probe |
| 8 | Explicit chat handoff | `explicit_handoff` | probe later |

## What The Fixtures Proved

The source-signal shape is small enough to describe the first product:

- A signal type.
- Source family.
- Scope keys.
- Evidence summary.
- Freshness.
- Confidence.
- Agent visibility.

The cards stay understandable when source content is withheld, stale, or
unavailable. That is important because TeamCtx should improve the agent's next
action without dumping source material into the prompt.

## Product Pressure Found

`approved_guidance` is overloaded.

For local notes, the signal is not necessarily approved project guidance. It may
only mean an approved folder produced an advisory clue. The language should
probably distinguish:

- `approved_guidance`: reviewed guidance that can appear under `Project guidance`.
- `advisory_match`: scoped source match that appears under `Good to know`.

This matters because Obsidian and Markdown folders can be valuable without being
authoritative.

## Recommended Signal Revision

Add `advisory_match` as a signal type before implementation.

Revised signal list:

- `collision`
- `changed_since_start`
- `stale_source`
- `unavailable_source`
- `blocked_source`
- `approved_guidance`
- `advisory_match`
- `explicit_handoff`
- `runtime_state`

## Engineering Implication

The backend should not start with a generic memory record. It should start with a
source signal envelope that can degrade safely:

```yaml
signal_type: advisory_match
source_family: local_notes
scope_keys:
  service: auth-service
freshness: fresh
confidence: medium
agent_visibility: visible
source_display: Obsidian folder Engineering/Auth
evidence_summary: Approved note folder mentions this auth flow.
```

The rendered card is a view over the signal, not the durable object itself.

## Product Decision

Use the fixture pack to drive benchmark scenarios and prototype data modeling.
Do not design connectors that return raw memory entries as the first abstraction.

## Next Experiment

Run a language/action test on `advisory_match` versus `approved_guidance`, because
this is the first place where the product could accidentally overstate source
authority.
