# E-016: Source Signal Fixtures

## Purpose

Create concrete fixtures for the first source-signal model.

E-015 says TeamCtx should start from signals, not connector count. This
experiment checks whether each launch/probe source can produce a small,
explainable working-context card without leaking private content or forcing the
agent to obey source text.

## Product Question

Can the first source families produce useful context cards with a small shared
shape?

## Hypothesis

The product can normalize many source families into a few signal types:

- `collision`
- `changed_since_start`
- `stale_source`
- `unavailable_source`
- `blocked_source`
- `approved_guidance`
- `explicit_handoff`
- `runtime_state`

If a source cannot map to one of these without broad search or private mining,
it should not be in the first product.

## Fixture Standard

Each fixture must include:

- Source input.
- Normalized signal.
- Working context card.
- What must not be shown.
- Expected agent behavior.

## Launch Source Families To Cover

- Local workspace and git metadata.
- Git hosting metadata.
- Issue tracker metadata.
- Configured or linked docs.
- Approved local notes.

## Probe Source Families To Cover

- CI/deploy systems.
- Explicit chat handoffs.

## Pass Criteria

The fixture pack is useful if:

- Every launch source produces at least one card that changes agent behavior.
- Every card can explain itself through `Show why`.
- Stale, unavailable, and blocked sources never become guidance.
- Approved local notes remain advisory unless reviewed into project guidance.
- Chat appears only through an explicit handoff marker.

## Stop Conditions

Stop and revise the source strategy if:

- A fixture requires broad workspace search to be useful.
- A fixture exposes private note, DM, email, or inaccessible document details.
- A fixture creates a vague warning the agent cannot act on.
- A fixture would make users feel monitored rather than helped.

## Output

A first source-signal fixture pack for product and engineering review.
