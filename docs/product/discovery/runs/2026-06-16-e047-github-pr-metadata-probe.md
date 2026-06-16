# E-047 Run: GitHub PR Metadata Probe

Date: 2026-06-16

## Created

- `src/teamctx/connectors/forge_review.py`
- `src/teamctx/connectors/github.py`
- `teamctx github-pr-probe` CLI command
- `tests/test_forge_review.py`

## Verification

Focused checks passed:

```bash
python3 -m pytest tests/test_forge_review.py -q
python3 -m ruff check src/teamctx/connectors src/teamctx/cli.py tests/test_forge_review.py
python3 -m mypy src/teamctx/connectors src/teamctx/cli.py tests/test_forge_review.py
```

Full verification is recorded with the commit that includes this run.

## Notes

This is not a general GitHub connector. It is a narrow probe for PR metadata and
changed paths. It intentionally excludes comments, patches, commit bodies, author
identity, and broad repo search.

The CLI returns a Core Contract V0 document. Missing credentials produce an
`unavailable` source status, not a hard crash and not silent confidence.
