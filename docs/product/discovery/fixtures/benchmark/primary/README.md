# Primary Benchmark Fixtures

Date: 2026-06-15

These fixtures implement the six primary E-014 benchmark scenarios.

## Fixtures

| Scenario | Fixture |
| --- | --- |
| 1. Overlapping file change | `primary-01-overlapping-file-change-v1.json` |
| 2. Changed acceptance criteria | `primary-02-changed-acceptance-criteria-v1.json` |
| 3. Stale process doc | `primary-03-stale-process-doc-v1.json` |
| 4. Safety-blocked source change | `primary-04-safety-blocked-source-change-v1.json` |
| 5. Inaccessible linked docs | `primary-05-inaccessible-linked-docs-v1.json` |
| 6. Project guidance applies | `primary-06-project-guidance-applies-v1.json` |

## Generate Prompts

Baseline:

```text
PYTHONPATH=src python3 -m teamctx.cli benchmark-prompt --variant baseline --fixture docs/product/discovery/fixtures/benchmark/primary/primary-01-overlapping-file-change-v1.json
```

Context:

```text
PYTHONPATH=src python3 -m teamctx.cli benchmark-prompt --variant context --fixture docs/product/discovery/fixtures/benchmark/primary/primary-01-overlapping-file-change-v1.json
```

`--scenario` is optional. If provided, it must match the fixture id or the fixture
id without its trailing version suffix.
