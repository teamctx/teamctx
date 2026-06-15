# E-030 Run: Benchmark Run Protocol V1

Date: 2026-06-15

Purpose: make the generated benchmark packet ready for model execution and score
capture.

## Code Change

`teamctx benchmark-export` now writes:

- `run-sheet.md`
- `run-order.md`
- `manifest.json`
- `score-sheet.csv`
- six baseline prompt files
- six context prompt files

The run order alternates first prompt by scenario:

- odd scenarios: baseline first,
- even scenarios: context first.

## Updated Packet

- `runs/2026-06-15-e029-primary-benchmark-export/run-order.md`
- `runs/2026-06-15-e029-primary-benchmark-export/manifest.json`
- `runs/2026-06-15-e029-primary-benchmark-export/score-sheet.csv`

## Verification

Passed:

```text
python3 -m compileall src/teamctx tests
python3 -m pytest
python3 -m ruff check .
python3 -m mypy src tests
grep -R -n -E 'memory|ledger|registry|promotion|quarantine|source signal|advisory match|authority tier|normalized artifact|durable core' docs/product/discovery/runs/2026-06-15-e029-primary-benchmark-export
```

Final observed results:

- pytest: 19 passed,
- ruff: all checks passed,
- mypy: no issues in 14 source files,
- exported packet banned-term scan: no matches.

## Product Result

The benchmark is now ready to run without hand reconstruction.

The next evidence step genuinely requires model execution: run the prompt packet
against at least one daily-driver model and one stronger reasoning model, then
score with the generated `score-sheet.csv` and E-014 rubric.

## Decision Boundary

This is a natural stop point for local-only experimentation. More local code now
risks optimizing the harness instead of learning whether working context improves
agent behavior.
