# E-035 Run: Claude Six Primary V1

Date: 2026-06-15

Purpose: run all six primary scenarios through Claude Code with baseline and
TeamCtx context variants, then score runtime economics and patch quality.

## Scope

- Scenarios: six primary benchmark fixtures.
- Model: `sonnet` (`claude-sonnet-4-6` as reported by Claude Code).
- Runs: 12 total, baseline and context for each scenario.
- Per-run cap: `$0.30`.

## Aggregate Runtime

- Baseline total reported cost: `0.8382276`.
- Context total reported cost: `0.9118254`.
- Context minus baseline: `0.0735978`.
- Baseline turns/tools/reads: `56` / `50` / `34`.
- Context turns/tools/reads: `60` / `54` / `35`.

## Quality

- Quality scorer after task-aware correction: `8 pass`, `4 review`, `0 fail`.
- Reviews were concentrated in scenarios with missing validation capture.
- No source snapshots were modified.

## Product Read

The broad economics result is mixed. TeamCtx context saved cost and tool work
on the two strongest direct-signal scenarios:

- same-file PR collision,
- changed acceptance criteria.

Across all six scenarios, context cost more overall. The largest regression was
the safety-blocked source scenario, where context caused deeper investigation
and more tool use. This does not mean context is bad; it means the product
cannot claim blanket token savings for every context card.

Better claim: TeamCtx saves lookup work when context is fresh, specific, and
task-changing. Warnings and source-health cards may intentionally spend extra
agent effort to prevent unsafe or incomplete work.

## Decision

The next product/engineering move is context gating, not connectors:

- identify which card types should be inserted into the agent prompt by default,
- identify which should live behind `show why` or source-health UI,
- separate cost-saving context from safety-preserving context in scoring.
