# E-036 Run: Agent Prompt Context Gating V1

Date: 2026-06-15

Purpose: turn the E-035 benchmark finding into a deterministic prompt-selection
rule.

## Change

TeamCtx now has two fixture-backed selection paths:

- `context_cards()`: rich context for terminal/user inspection.
- `agent_prompt_cards()`: the stricter set injected into generated agent
  prompts.

The default agent prompt gate allows fresh visible action cards and active fresh
project guidance. Stale, unavailable, and blocked source-health cards are not
injected by default, but can still be included through explicit session selection
or relevance.

## Primary Scenario Outcome

| Scenario | Default prompt card? | Product read |
| --- | --- | --- |
| `primary-01-overlapping-file-change-v1` | yes | Fresh same-file collision can save lookup. |
| `primary-02-changed-acceptance-criteria-v1` | yes | Fresh changed task criteria can save lookup. |
| `primary-03-stale-process-doc-v1` | no | Source-health warning, not default cost-saving context. |
| `primary-04-safety-blocked-source-change-v1` | no | Blocked-source warning belongs in inspection/safety surfaces. |
| `primary-05-inaccessible-linked-docs-v1` | no | Availability warning belongs in source-health surfaces. |
| `primary-06-project-guidance-applies-v1` | yes | Active project guidance remains agent-relevant. |

## Generated Packet

`docs/product/discovery/runs/2026-06-15-e036-gated-benchmark-export/`

The packet is a new historical artifact. The older E-029 export remains unchanged
because it represents the pre-gate benchmark prompts.

## Product Read

This makes the token-savings claim more credible:

TeamCtx saves lookup work when it supplies fresh, specific, task-changing
context. It should not automatically spend prompt budget on every warning it can
explain. Warnings stay valuable, but they are a separate source-health and
confidence product surface.

## Verification

Focused verification:

- `python3 -m pytest tests/test_benchmark_fixtures.py tests/test_fixture_prototype.py`
- Result: `20 passed`.

Full verification:

- `python3 -m compileall -q src tests`
- `python3 -m pytest`
- `python3 -m ruff check .`
- `python3 -m mypy src tests`

Results:

- compileall: passed.
- pytest: `39 passed`.
- Ruff: all checks passed.
- mypy: no issues in `18` source files.
