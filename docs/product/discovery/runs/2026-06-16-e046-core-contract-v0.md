# E-046 Run: Core Contract V0

Date: 2026-06-16

## Created

- `src/teamctx/core/contracts.py`
- `src/teamctx/fixtures.py`
- `docs/product/discovery/fixtures/contracts/v0/core-contract-document.json`
- `tests/test_core_contracts.py`
- `docs/product/discovery/architecture/core-contract-v0.md`

## Verification

Focused checks passed:

```bash
python3 -m pytest tests/test_core_contracts.py -q
python3 -m ruff check src/teamctx/core/contracts.py src/teamctx/core/fixtures.py src/teamctx/fixtures.py tests/test_core_contracts.py
python3 -m mypy src/teamctx/core/contracts.py src/teamctx/core/fixtures.py src/teamctx/fixtures.py tests/test_core_contracts.py
```

Full verification is recorded with the commit that includes this run.

## Notes

The core package now validates parsed data only. File I/O for fixtures is handled
by `teamctx.fixtures`. This keeps the live connector work from growing around an
impure core boundary.
