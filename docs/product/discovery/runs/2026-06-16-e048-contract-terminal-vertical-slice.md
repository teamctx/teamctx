# E-048 Run: Contract Terminal Vertical Slice

Date: 2026-06-16

## Created

- `src/teamctx/contract_documents.py`
- `src/teamctx/contract_render.py`
- `teamctx refresh`
- `teamctx context --contract`
- `teamctx why --contract`
- `teamctx open-source --contract`
- `tests/test_contract_terminal.py`

## Verification

Focused checks passed:

```bash
python3 -m pytest tests/test_contract_terminal.py tests/test_fixture_prototype.py tests/test_source_open.py tests/test_forge_review.py -q
python3 -m ruff check src/teamctx/contract_documents.py src/teamctx/contract_render.py src/teamctx/cli.py tests/test_contract_terminal.py
python3 -m mypy src/teamctx/contract_documents.py src/teamctx/contract_render.py src/teamctx/cli.py tests/test_contract_terminal.py
```

Full verification is recorded with the commit that includes this run.

## Notes

`refresh` intentionally writes source status even when GitHub credentials are
missing. That keeps missing configured context visible without pretending the
source was healthy.
