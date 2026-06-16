# Status Open Six Primary Comparison

Compares E-043 `status_open` against the E-035 six-primary context/full-source run.

## Aggregate

| Metric | Full source | Status open | Status open delta |
| --- | ---: | ---: | ---: |
| Reported cost | 0.911825 | 0.788972 | -0.122854 (-13.5%) |
| Turns | 60 | 49 | -11 |
| Tool calls | 54 | 43 | -11 |
| Files read | 35 | 21 | -14 |
| Bash commands | 6 | 13 | 7 |

## Per Scenario

| Scenario | Full cost | Status open cost | Delta | Quality | Read |
| --- | ---: | ---: | ---: | --- | --- |
| `primary-01-overlapping-file-change-v1` | 0.117811 | 0.075760 | -0.042052 | review 7/8 | Cheaper, but review: agent noticed same-file PR and still changed existing `rotate_token` API. |
| `primary-02-changed-acceptance-criteria-v1` | 0.173647 | 0.212760 | 0.039114 | pass 7/7 | More expensive than prior full-source run, but opened Jira, added tests, and passed. |
| `primary-03-stale-process-doc-v1` | 0.121392 | 0.097685 | -0.023708 | pass 6/6 | Cheaper than full source and status-only; opened stale source and preserved stale caveat. |
| `primary-04-safety-blocked-source-change-v1` | 0.230924 | 0.098501 | -0.132423 | pass 6/6 | Cheaper than full source; slightly costlier than status-only; blocked after denied Jira body. |
| `primary-05-inaccessible-linked-docs-v1` | 0.141825 | 0.112791 | -0.029034 | pass 6/6 | Cheaper than full source; costlier than status-only; blocked without source body. |
| `primary-06-project-guidance-applies-v1` | 0.126227 | 0.191476 | 0.065249 | pass 7/7 | More expensive than full source but passed; no source body was needed. |

## Warning Scenario Check

Against E-040 status-only on stale/blocked/unavailable warning scenarios, `status_open` was mixed:

| Scenario | Status-only cost | Status-open cost | Delta |
| --- | ---: | ---: | ---: |
| `primary-03-stale-process-doc-v1` | 0.106970 | 0.097685 | -0.009286 |
| `primary-04-safety-blocked-source-change-v1` | 0.083336 | 0.098501 | 0.015164 |
| `primary-05-inaccessible-linked-docs-v1` | 0.092515 | 0.112791 | 0.020276 |
| **Total** | 0.282821 | 0.308976 | 0.026155 |

## Product Read

`status_open` is better than full source access as a broad replacement for source snapshots, but it is not better than compact status-only everywhere. The product should default to compact source status and expose source opening as an on-demand capability when a source body is available and likely to change the task.

The benchmark helper was hardened during E-043: the visible workspace contains `.teamctx/open_source.py`, but no `.teamctx/source-data.json` and no temp source-data path. The opener reads its backing payload through `TEAMCTX_SOURCE_OPEN_DATA`, which is a benchmark stand-in for a future MCP/read-only tool boundary.

Open questions from this run:

- Source status should probably say whether body text is available before the agent spends a tool call opening it.
- Same-file collision guidance needs a stronger patch-quality rule: noticing a collision is not enough if the agent still changes the existing API.
- Opening sources through a script is acceptable for benchmarks, but the product surface should likely be an MCP read-only tool, with the CLI command as a human/debug surface.
