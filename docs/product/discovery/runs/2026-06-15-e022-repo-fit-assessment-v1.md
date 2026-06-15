# E-022 Run: Repo Fit Assessment V1

Date: 2026-06-15

Purpose: assess whether the fixture-backed prototype fits the existing repo.

## Created Artifact

- `architecture/repo-fit-assessment-v1.md`

## Finding

The repo is ready for a fixture-backed prototype without a restructure.

Current code is small:

- `src/teamctx/cli.py`
- `src/teamctx/__init__.py`

Existing dependencies already cover the prototype:

- `click` for CLI,
- `pydantic` for fixture/model validation,
- `pytest` for golden tests.

## Important Adjustment

Do not create a separate installable `teamctx-core` package yet.

Keep the boundary inside the package first:

```text
src/teamctx/core/
```

This preserves the architectural idea without spending complexity before product
proof.

## Existing Docs Fit

The old docs are not wrong. They are just one layer lower or broader than the new
product thesis.

Best mapping:

- artifacts: normalized provider facts,
- relationships: why source facts connect to the current work,
- source signals: task-scoped conclusions or caveats,
- context cards: user-facing rendered output.

## Recommendation

Next implementation should be fixture-backed and internal-boundary-first:

1. `teamctx.core.signals`
2. `teamctx.core.guidance`
3. `teamctx.core.fixtures`
4. `teamctx.render`
5. CLI commands in existing `teamctx.cli`
6. golden tests

No connector work yet.

## Product Interpretation

This is still one product.

`teamctx-core` is an architecture boundary, not a product surface, not a docs term
for users, and not a separate install step in the first prototype.
