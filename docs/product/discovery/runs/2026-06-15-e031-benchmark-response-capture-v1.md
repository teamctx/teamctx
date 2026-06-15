# E-031 Run: Benchmark Response Capture V1

Date: 2026-06-15

Purpose: make the benchmark packet ready to collect raw model answers and
score them without extra manual setup.

## Code Change

`teamctx benchmark-export` now writes:

- `responses/README.md`
- `results/README.md`
- response path columns in `score-sheet.csv`

The response path convention is:

- `responses/{model}/{fixture_id}-baseline.md`
- `responses/{model}/{fixture_id}-context.md`

## Updated Packet

- `runs/2026-06-15-e029-primary-benchmark-export/responses/README.md`
- `runs/2026-06-15-e029-primary-benchmark-export/results/README.md`
- `runs/2026-06-15-e029-primary-benchmark-export/score-sheet.csv`

## Verification

Passed:

```text
PYTHONPATH=src python3 -m compileall src/teamctx tests
PYTHONPATH=src python3 -m pytest
PYTHONPATH=src python3 -m ruff check .
PYTHONPATH=src python3 -m mypy src tests
grep -R -n -E 'memory|ledger|registry|promotion|quarantine|source signal|advisory match|authority tier|normalized artifact|durable core' docs/product/discovery/runs/2026-06-15-e029-primary-benchmark-export
```

Final observed results:

- compileall: passed,
- pytest: 19 passed,
- ruff: all checks passed,
- mypy: no issues in 14 source files,
- exported packet banned-term scan: no matches.

## Product Result

The local harness is ready for a real paired model pilot. The next step is
to run the packet against one daily-driver model and one stronger reasoning
model, then score the paired answers.
