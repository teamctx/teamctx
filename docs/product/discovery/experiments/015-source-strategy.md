# E-015: Source Strategy

## Purpose

Decide which source families belong in the first product shape, and define the
standard a source must meet before it becomes a connector.

The product risk is obvious: if TeamCtx pulls from everywhere, it becomes a
creepy tracker, a noisy enterprise search tool, or a token-wasting summary layer.
This experiment defines the narrower path.

## Product Question

Where should working context come from at first?

## Hypothesis

TeamCtx should connect to fewer source families than expected, but turn those
sources into better task-changing signals.

A source should be included only when it can answer at least one of these:

- Has something changed since this branch, task, or session started?
- Is someone else touching the same work surface?
- Is the source stale, inaccessible, blocked, or unsafe to rely on?
- Is there approved project guidance that changes how this task should be done?
- Is there an explicit handoff for this work?
- Is there a current build, release, or incident state that changes the next
  action?

## Inclusion Bar

A first-product source must satisfy all of these:

- Produces scoped signals, not broad summaries.
- Has user or team intent behind its inclusion.
- Can be explained with `Show why`.
- Has a safe failure state when stale, blocked, or unavailable.
- Does not require broad surveillance of private work.
- Improves agent behavior in the benchmark or a source probe.

## Exclusion Bar

Do not include a source in the first product when it primarily produces:

- Presence, productivity, sentiment, or activity tracking.
- Private messages or private notes.
- Broad search results with no task scope.
- Summaries that cannot be verified.
- Context that requires the agent to obey source text as instruction.

## Method

Create a source-family matrix and assign each source one of four launch decisions:

- `launch`: belongs in first product experiments.
- `probe`: worth testing with fixtures before implementation.
- `later`: plausible, but not needed to validate the core product.
- `exclude`: wrong shape for this product.

## Output

A launch-source recommendation and source-signal model for the next benchmark and
prototype planning.
