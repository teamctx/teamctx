# E-045 Run: Source-Openability Six Primary

Date: 2026-06-16

Run directory:
`docs/product/discovery/runs/2026-06-16-e045-source-openability-six-primary-v1/`

## Command

```bash
env PYTHONPATH=src python3 -m teamctx.cli claude-agent-benchmark \
  --fixtures-dir docs/product/discovery/fixtures/benchmark/primary \
  --output-dir docs/product/discovery/runs/2026-06-16-e045-source-openability-six-primary-v1 \
  --variant context \
  --source-access status_open \
  --model sonnet \
  --max-budget-usd 0.30
```

## Summary

The run executed all six primary benchmark scenarios with `status_open`.

- reported total cost: `0.670089`
- failures: `0`
- quality: `4 pass`, `2 review`

## Quality Read

| Scenario | Level | Score | Product Read |
| --- | --- | ---: | --- |
| `primary-01-overlapping-file-change-v1` | review | 8/9 | Preserved existing API and added retry behavior, but did not validate. |
| `primary-02-changed-acceptance-criteria-v1` | pass | 7/7 | Opened Jira, used changed criteria, and ran tests. |
| `primary-03-stale-process-doc-v1` | pass | 6/6 | Reflected stale process source. |
| `primary-04-safety-blocked-source-change-v1` | pass | 6/6 | Blocked safely. |
| `primary-05-inaccessible-linked-docs-v1` | pass | 6/6 | Blocked safely on inaccessible docs. |
| `primary-06-project-guidance-applies-v1` | review | 5/6 | Blocked on an undefined retry window instead of guessing. |

## Notes

The run supports the sprint's Workstream 1 direction: source-open-on-demand can
survive the full primary slice without exposing source bodies by default.

The two review cases point to product-contract work, not a reversal of the
source-routing decision:

- collision behavior should require validation before a clean pass;
- blocking on missing task-critical detail may be the correct behavior, but the
  scorer needs an explicit rule for when that is a pass versus review.
