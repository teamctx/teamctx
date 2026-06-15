# E-036: Agent Prompt Context Gating

## Purpose

Separate rich TeamCtx inspection context from the smaller set of cards that
should enter an agent prompt by default.

## Product Question

Can TeamCtx preserve useful source-health information without spending agent
attention on warnings that did not save lookup work in the E-035 benchmark?

## Hypothesis

Default prompt context should be limited to:

- fresh visible action context, such as same-file collisions and changed task
  criteria,
- active fresh project guidance.

Stale, unavailable, and blocked source-health cards should remain visible in
rich context surfaces and explicit session selections, but should not be injected
into the default agent prompt.

## Pass Criteria

- Benchmark and Claude-agent prompt generation use the prompt gate.
- The `context` command still shows rich context for source-health inspection.
- Primary scenarios 1, 2, and 6 keep prompt context by default.
- Primary scenarios 3, 4, and 5 have no default prompt context.
- Tests, Ruff, and mypy pass.

## Output

- `src/teamctx/core/cards.py` prompt gate.
- `agent_prompt_cards()` helper for agent-facing call sites.
- `runs/2026-06-15-e036-gated-benchmark-export/` prompt packet.
