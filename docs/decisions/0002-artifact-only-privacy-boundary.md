# ADR 0002: Artifact-Only Privacy Boundary

- Status: accepted
- Date: 2026-06-14

## Context

The product needs ambient context without monitoring people. Team systems contain
both useful operational facts and sensitive human information.

## Decision

`teamctx` observes approved shared artifacts, not people.

Private messages, local activity, prompts, responses, presence, productivity
signals, sentiment, and interpersonal judgments are outside the product boundary.

## Consequences

- Connectors must be narrow and opt-in.
- People-derived analytics are not a feature category.
- Artifact metadata may be used only when already visible to the requester and
  necessary for the card.
- The product can say what it did not collect because those collectors do not
  exist.

