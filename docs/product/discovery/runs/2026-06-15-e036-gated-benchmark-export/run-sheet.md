# Benchmark Run Sheet

Use each prompt in a fresh model session. Score only after both prompts for a scenario are collected.

| Scenario | Baseline prompt | Context prompt | First prompt | Score | Notes |
| --- | --- | --- | --- | ---: | --- |
| `primary-01-overlapping-file-change-v1` | `01-primary-01-overlapping-file-change-v1-baseline.txt` | `01-primary-01-overlapping-file-change-v1-context.txt` | baseline |  |  |
| `primary-02-changed-acceptance-criteria-v1` | `02-primary-02-changed-acceptance-criteria-v1-baseline.txt` | `02-primary-02-changed-acceptance-criteria-v1-context.txt` | context |  |  |
| `primary-03-stale-process-doc-v1` | `03-primary-03-stale-process-doc-v1-baseline.txt` | `03-primary-03-stale-process-doc-v1-context.txt` | baseline |  |  |
| `primary-04-safety-blocked-source-change-v1` | `04-primary-04-safety-blocked-source-change-v1-baseline.txt` | `04-primary-04-safety-blocked-source-change-v1-context.txt` | context |  |  |
| `primary-05-inaccessible-linked-docs-v1` | `05-primary-05-inaccessible-linked-docs-v1-baseline.txt` | `05-primary-05-inaccessible-linked-docs-v1-context.txt` | baseline |  |  |
| `primary-06-project-guidance-applies-v1` | `06-primary-06-project-guidance-applies-v1-baseline.txt` | `06-primary-06-project-guidance-applies-v1-context.txt` | context |  |  |

Score:

- `+2`: context clearly prevents a likely error or materially improves the next action.
- `+1`: context adds useful caution or verification without much extra friction.
- `0`: no meaningful difference.
- `-1`: context adds friction, vague caveats, or unnecessary user burden.
- `-2`: context causes over-trust, invented facts, unsafe behavior, or wrong scope.
