# E-033 Run: Claude Agent Runtime V1

Date: 2026-06-15

Purpose: run the first real Claude Code agent-runtime benchmark with and
without TeamCtx working context.

## Scope

- Scenario: `primary-01-overlapping-file-change-v1`
- Model: `sonnet` (`claude-sonnet-4-6` as reported by Claude Code)
- Variants: baseline, context
- Harness output: `runs/2026-06-15-e033-claude-agent-runtime-v1/`

## Metrics

| Variant | Cost | Duration | Turns | Tools | Files read | Output tokens |
| --- | ---: | ---: | ---: | ---: | ---: | ---: |
| baseline | 0.1721997 | 36561 ms | 8 | 7 | 4 | 1836 |
| context | 0.1064415 | 31345 ms | 7 | 6 | 3 | 1763 |

Delta:

- Cost: -0.0657582 reported USD, about 38% lower.
- Duration: -5216 ms.
- Turns: -1.
- Tool calls: -1.
- Files read: -1.

## Quality Read

The economics signal is positive: the context run reached a useful action with
less reported cost and less tool work.

The quality signal is mixed. The baseline discovered PR #482 by looking through
local source snapshots and produced a conservative additive helper. The context
run used the PR collision sooner and did less lookup work, but modified the
existing `rotate_token` function directly. That may be acceptable, but it is not
an unambiguous quality improvement.

## Product Read

This is the first direct support for the Ambara-era economics claim inside the
TeamCtx framing: scoped working context can reduce lookup work and reported
agent cost. It also shows why quality scoring must stay separate from economics
scoring.

## Next

Before running all six scenarios, add explicit quality scoring for diffs so a
cheaper run is not mistaken for a better run.
