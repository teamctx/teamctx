# E-034: Claude Quality Scoring

## Purpose

Add deterministic patch-quality scoring to the Claude agent runtime benchmark
before scaling beyond the first scenario.

## Product Question

Can we keep the economics claim separate from patch quality so lower token
cost is never mistaken for a better outcome?

## Hypothesis

A first deterministic scorer should classify saved runs by completion, target
file touch, source-snapshot safety, risk awareness, task relevance, validation,
and scenario-specific API preservation.

## Output

- `src/teamctx/claude_quality.py` quality scorer.
- `teamctx claude-agent-assess` CLI command.
- `quality.csv` and `quality.md` for E-033.
