# E-006 Agent Consumption Benchmark

## Question

Does working context measurably improve agent-terminal work?

## Hypothesis

A small working-context packet will reduce lookup time, token usage, repeated
explanation, and missed constraints without causing the agent to over-trust stale
or advisory context.

## Benchmark Shape

Create paired runs for the same task:

- baseline: no TeamCtx context
- context: terminal context surface included at start or resume

Use tasks where context plausibly matters:

1. overlapping file change
2. changed Jira or Linear acceptance criteria
3. changed process doc
4. saved project guidance applies
5. source unavailable or stale
6. private/blocked source omitted
7. explicit chat handoff applies
8. Obsidian/Markdown note is advisory only

## Measures

Primary:

- Was the final answer correct?
- Did the agent notice the relevant constraint?
- Did the agent over-trust stale/advisory context?
- Did the human need to intervene?

Secondary:

- Tokens used.
- Tool calls or source lookups avoided.
- Time to useful action.
- Number of irrelevant context items shown.

## Pass Criteria

Across the first 10 paired tasks:

- Context improves or preserves correctness in at least 7.
- Context causes no severe over-trust errors.
- Average irrelevant shown items are below 1 per task.
- At least 3 tasks avoid a source lookup or repeated explanation.

## Fail Criteria

- Context is mostly ignored.
- Context encourages premature certainty.
- Context packets become long enough to skim past.
- Tool/source lookup savings are not visible.

## Decision

Pending.
