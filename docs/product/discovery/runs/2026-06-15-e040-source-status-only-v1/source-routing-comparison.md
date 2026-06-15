# Source Routing Comparison

Compares E-040 source-access `status_only` against the prior warning-scenario runs: E-035 baseline/full source, E-037 gated/full source, and E-039 gated/no source.

## Aggregate

| Metric | E-035 baseline | E-037 gated/full source | E-039 gated/no source | E-040 gated/status-only | Status-only vs baseline | Status-only vs full source | Status-only vs no source |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| Reported cost | 0.354957 | 0.447406 | 0.287766 | 0.282821 | -0.072136 | -0.164585 | -0.004944 |
| Turns | 28 | 30 | 22 | 21 | -7 | -9 | -1 |
| Tool calls | 25 | 27 | 19 | 18 | -7 | -9 | -1 |
| Files read | 20 | 21 | 14 | 9 | -11 | -12 | -5 |

## Per Scenario

| Scenario | Status-only cost | Delta vs baseline | Delta vs full source | Delta vs no source | Turn delta vs full source | Tool delta vs full source | Read delta vs full source | Quality | Behavior |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | --- | --- |
| `primary-03-stale-process-doc-v1` | 0.106970 | -0.015818 | -0.078936 | -0.002243 | -2 | -2 | -1 | pass 6/6 | Drafted checklist from local files and marked stale Confluence risk. |
| `primary-04-safety-blocked-source-change-v1` | 0.083336 | -0.016902 | -0.049548 | -0.006073 | -5 | -5 | -5 | pass 6/6 | Blocked instead of guessing at a safety-filtered Jira change. |
| `primary-05-inaccessible-linked-docs-v1` | 0.092515 | -0.039416 | -0.036101 | 0.003372 | -2 | -2 | -6 | pass 6/6 | Blocked because linked docs were inaccessible. |

## Read

Status-only source routing is the best current default candidate. It preserves the useful warnings from source state without handing the agent a browsable source dump.

In this three-scenario smoke, status-only was slightly cheaper than no source and materially cheaper than full source while preserving 3/3 pass quality. More importantly, it fixed the key product flaw from E-039: the agent no longer treated a stale local export as silently good enough.

The product implication is plain: TeamCtx should route compact source health into the agent by default, and keep source bodies out of the workspace unless the user or policy explicitly asks for them.
