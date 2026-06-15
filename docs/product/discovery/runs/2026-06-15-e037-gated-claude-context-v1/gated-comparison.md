# Gated Context Comparison

Compares the E-037 gated context rerun against the E-035 baseline and old context runs for the three scenarios whose prompt cards changed.

## Aggregate

| Metric | E-035 baseline | E-035 old context | E-037 gated context | Gated vs baseline | Gated vs old context |
| --- | ---: | ---: | ---: | ---: | ---: |
| Reported cost | 0.354957 | 0.494141 | 0.447406 | 0.092449 | -0.046735 |
| Turns | 28 | 36 | 30 | 2 | -6 |
| Tool calls | 25 | 33 | 27 | 2 | -6 |
| Files read | 20 | 24 | 21 | 1 | -3 |

## Per Scenario

| Scenario | Gated cost vs baseline | Gated cost vs old context | Turn delta vs old | Tool delta vs old | Read delta vs old | Gated quality |
| --- | ---: | ---: | ---: | ---: | ---: | --- |
| `primary-03-stale-process-doc-v1` | 0.063118 | 0.064513 | -1 | -1 | -2 | pass 6/6 |
| `primary-04-safety-blocked-source-change-v1` | 0.032646 | -0.098039 | -3 | -3 | 0 | pass 6/6 |
| `primary-05-inaccessible-linked-docs-v1` | -0.003314 | -0.013209 | -2 | -2 | -1 | pass 6/6 |

## Read

Gating reduced the old warning-context overhead for the changed scenario set, especially the blocked-source scenario. It did not beat baseline overall.

The harness still tells every variant that local source snapshots may exist and exposes all snapshots in the disposable workspace. Even when TeamCtx injects no default card, the agent can rediscover stale, blocked, or inaccessible-source evidence by browsing the snapshot directory.

Product implication: prompt gating is necessary but not sufficient for the token-savings claim. The next lever is source access routing: give the agent high-value context by default, keep source-health material inspectable, and avoid presenting every source snapshot as an attractive search space unless the task calls for it.
