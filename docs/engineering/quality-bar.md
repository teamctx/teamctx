# Quality Bar

## Standard

`teamctx` is built as infrastructure that cautious teams can inspect and
trust. The project should prefer narrow, deterministic, well-tested behavior over
broad claims.

## Release Gates

Before any public release:

- `pytest` passes.
- `ruff check .` passes.
- `mypy src` passes in strict mode.
- `git diff --check` passes.
- Public claims are covered by tests or removed.
- Security/privacy docs match implementation.

## Architecture Gates

- `teamctx.core` has no I/O.
- Live connectors cannot bypass central policy.
- Source text is untrusted everywhere.
- Every context card has provenance.
- Every omission is counted.
- Missing source health is represented honestly.

## Testing Strategy

- Unit tests for pure core rules.
- Property tests for policy and relevance invariants.
- Fixture-backed production-day simulations.
- Connector conformance tests before live connector claims.
- Golden tests for card output shape.
- Failure-path tests for unavailable, stale, unsafe, and malformed sources.

## Documentation Policy

Update docs in the same change when:

- A product claim changes.
- A connector support level changes.
- A card kind is added or changed.
- A security/privacy boundary changes.
- A CLI or API surface changes.
- An architectural decision is made.

