# Source Access Comparison

Compares E-039 source-access `none` against E-037 gated context with full source snapshots and the E-035 baseline for the three warning scenarios.

## Aggregate

| Metric | E-035 baseline | E-037 gated/full source | E-039 gated/no source | No source vs baseline | No source vs full source |
| --- | ---: | ---: | ---: | ---: | ---: |
| Reported cost | 0.354957 | 0.447406 | 0.287766 | -0.067191 | -0.159641 |
| Turns | 28 | 30 | 22 | -6 | -8 |
| Tool calls | 25 | 27 | 19 | -6 | -8 |
| Files read | 20 | 21 | 14 | -6 | -7 |

## Per Scenario

| Scenario | No source cost vs baseline | No source cost vs full source | Turn delta vs full source | Tool delta vs full source | Read delta vs full source | Quality |
| --- | ---: | ---: | ---: | ---: | ---: | --- |
| `primary-03-stale-process-doc-v1` | -0.013574 | -0.076692 | -1 | -1 | 0 | pass 6/6 |
| `primary-04-safety-blocked-source-change-v1` | -0.010829 | -0.043475 | -4 | -4 | -3 | pass 6/6 |
| `primary-05-inaccessible-linked-docs-v1` | -0.042788 | -0.039473 | -3 | -3 | -4 | pass 6/6 |

## Read

Withholding broad source snapshots materially reduced cost and lookup work on the warning scenario set while preserving pass-level benchmark quality.

This does not mean the product should hide all source state. In scenario 3, the agent updated the release checklist from the local stale export without knowing the upstream source-health caveat. In scenarios 4 and 5, source absence pushed the agent to block quickly instead of exploring the unavailable or blocked source evidence.

Product implication: the strongest shape is likely status-only source routing. Give agents compact source state when it changes confidence, but do not expose every source body as a browsable workspace by default.
