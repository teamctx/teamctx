# E-028 Run: Executable Benchmark Fixtures V1

Date: 2026-06-15

Purpose: make the first six E-014 benchmark scenarios executable from fixtures.

## Created Artifacts

- `fixtures/benchmark/primary/README.md`
- `fixtures/benchmark/primary/primary-01-overlapping-file-change-v1.json`
- `fixtures/benchmark/primary/primary-02-changed-acceptance-criteria-v1.json`
- `fixtures/benchmark/primary/primary-03-stale-process-doc-v1.json`
- `fixtures/benchmark/primary/primary-04-safety-blocked-source-change-v1.json`
- `fixtures/benchmark/primary/primary-05-inaccessible-linked-docs-v1.json`
- `fixtures/benchmark/primary/primary-06-project-guidance-applies-v1.json`
- `tests/test_benchmark_fixtures.py`

## Code Change

`teamctx benchmark-prompt` no longer hard-codes `auth-token-retry`.

It now accepts any fixture and uses `--scenario` only as an optional consistency
check against the fixture id.

## Product Result

The benchmark pack now exercises the same product mechanism as the prototype:

- fixture model,
- context card selection,
- prompt rendering,
- evidence-only instruction,
- banned-term checks.

This reduces the risk that benchmark prompts drift away from the actual terminal
surface.

## Verification

Passed:

```text
python3 -m pytest tests/test_benchmark_fixtures.py
python3 -m compileall src/teamctx tests
python3 -m pytest
python3 -m ruff check .
python3 -m mypy src tests
```

Final observed results:

- focused benchmark tests: 5 passed,
- full pytest: 16 passed,
- ruff: all checks passed,
- mypy: no issues in 13 source files.

CLI smoke test passed for scenario 5:

```text
PYTHONPATH=src python3 -m teamctx.cli benchmark-prompt --variant context --fixture docs/product/discovery/fixtures/benchmark/primary/primary-05-inaccessible-linked-docs-v1.json
```

## Next Product Evidence

Run the generated prompt pairs against at least one daily-driver model and one
stronger reasoning model.

Do not start real connectors until the benchmark shows the working context
improves or preserves agent behavior without over-trust.
