# E-049 Run: Project Config Refresh

Date: 2026-06-16

## Created

- `src/teamctx/project_config.py`
- `docs/product/discovery/fixtures/project-config/teamctx-config-v0.json`
- `tests/test_project_config.py`
- `teamctx refresh --config ...` support

## Verification

Focused checks passed:

```bash
python3 -m pytest tests/test_project_config.py tests/test_contract_terminal.py -q
python3 -m ruff check src/teamctx/project_config.py src/teamctx/cli.py tests/test_project_config.py tests/test_contract_terminal.py
python3 -m mypy src/teamctx/project_config.py src/teamctx/cli.py tests/test_project_config.py tests/test_contract_terminal.py
```

Full verification is recorded with the commit that includes this run.

## Notes

Project config rejects unknown fields and does not store credentials. It stores
only the environment variable name used to find the token at runtime.
