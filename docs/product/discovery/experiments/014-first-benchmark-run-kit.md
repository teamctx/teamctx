# E-014: First Benchmark Run Kit

## Purpose

Turn the E-011 benchmark pack into a runnable artifact for model testing.

This experiment should answer whether the current TeamCtx product shape helps an
agent terminal do better work when the task has missing, changed, stale, blocked,
or scoped project context.

## Inputs

- E-011 benchmark pack v2.
- E-012 readiness desk-check.
- E-013 scenario revisions.
- Current provisional language set.

## What This Is Testing

- Does `Working context` improve behavior without becoming instruction text?
- Do agents handle source caveats correctly?
- Does saved project guidance change implementation assumptions in the intended
  scope?
- Does the context prevent false confidence?
- Does the language cause confusion?

## What This Is Not Testing

- Connector correctness.
- Retrieval ranking.
- Full UI quality.
- User onboarding.
- Whether every possible source family is valuable.

## Method

Run paired prompts for each primary scenario:

1. Baseline prompt without working context.
2. Context prompt with the same task plus the working context block.

Keep the task wording identical between the pair. Do not tell the model what the
scenario is testing.

Run at least two models if possible:

- One fast/cheap daily-driver model.
- One stronger reasoning model.

If a model is nondeterministic, run each pair twice before judging.

## Scoring

For each scenario, score the context run against the baseline:

- `+2`: context clearly prevents a likely error or materially improves the next
  action.
- `+1`: context adds useful caution or verification without much extra friction.
- `0`: no meaningful difference.
- `-1`: context adds friction, vague caveats, or unnecessary user burden.
- `-2`: context causes over-trust, invented facts, unsafe behavior, or wrong
  scope.

Also mark:

- `over_trust`: the model treats source-backed context as command or fact beyond
  what was shown.
- `language_confusion`: the model appears confused by labels such as `Working
  context`, `Project guidance`, or `Verify before relying`.
- `token_waste`: the model spends substantial output explaining the context
  system instead of doing the task.
- `lookup_saved`: the model avoids a needless rediscovery step or asks a more
  precise verification question.

## Pass Criteria

Across the six primary scenarios:

- Total score is at least `+6`.
- At least five context runs score `+1` or better.
- No scenario scores `-2`.
- No more than one scenario has language confusion.
- At least three scenarios show `lookup_saved` or an avoided false assumption.

## Stop Conditions

Stop and revise the product language or surface if:

- Two or more scenarios show over-trust.
- The model treats working context as a hidden instruction layer.
- The model repeatedly asks the user to paste sensitive or blocked source text.
- The model spends more time managing TeamCtx than doing the task.

## Output

Create a run note with:

- Model and settings.
- Prompt pair order.
- Baseline response summary.
- Context response summary.
- Score and flags.
- Product interpretation.
- Any language changes to test next.

## Decision Rule

If the first run passes, continue to secondary scenarios and a language variant
track.

If it fails, revise the context surface before any connector or backend build
planning.
