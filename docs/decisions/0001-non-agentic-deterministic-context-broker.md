# ADR 0001: Non-Agentic Deterministic Context Broker

- Status: accepted
- Date: 2026-06-14

## Context

The product needs to distribute useful team context to developers and coding
agents without becoming an agent, surveillance system, or broad AI search layer.

Generative systems can be useful at the consumption layer, but the context broker
itself must be predictable, inspectable, and safe enough to sit between team
systems of record and developer tools.

## Decision

`teamctx` will not use an LLM or autonomous agent behavior in the context broker.

The product emits deterministic context cards from normalized artifacts,
relationships, policy checks, and explicit rules.

## Consequences

- The core product can be tested with exact expected outputs.
- Product claims depend on rules and fixtures, not model quality.
- Important team knowledge should be represented as structured artifact fields
  or explicit rule blocks rather than inferred from arbitrary prose.
- The system will be less magical than AI search, but more auditable and safer.

