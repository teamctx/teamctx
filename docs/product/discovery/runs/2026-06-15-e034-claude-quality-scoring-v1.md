# E-034 Run: Claude Quality Scoring V1

Date: 2026-06-15

Purpose: score the saved E-033 Claude Code benchmark artifacts for patch
quality separately from runtime economics.

## Code Change

Added deterministic assessment for:

- clean run completion,
- target-file changes,
- source-snapshot safety,
- final benchmark result block presence,
- risk awareness,
- retry-behavior relevance,
- validation attempt,
- API preservation for the same-file collision scenario.

## Output

- `runs/2026-06-15-e033-claude-agent-runtime-v1/quality.csv`
- `runs/2026-06-15-e033-claude-agent-runtime-v1/quality.md`

## Result

| Variant | Quality | Score | Notes |
| --- | --- | ---: | --- |
| baseline | review | 7/8 | no validation command or test change captured |
| context | review | 6/8 | no validation command or test change captured; changed existing `rotate_token` API in collision scenario |

## Product Read

E-033 remains a positive economics signal for TeamCtx context, but E-034 keeps
the quality read honest. The context run spent less and did less lookup work;
the baseline produced a more conservative patch shape.

The product claim should therefore stay two-dimensional:

- TeamCtx can reduce agent lookup work and reported cost.
- TeamCtx must also preserve or improve patch quality before it earns a broader
  product claim.

## Next

Run all six primary scenarios only after the quality scorer is part of the
standard benchmark output.
