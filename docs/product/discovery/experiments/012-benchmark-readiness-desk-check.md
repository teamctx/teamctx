# E-012 Benchmark Readiness Desk Check

## Question

Are the E-011 benchmark scenarios fair tests of TeamCtx context value, or are
they too leading, artificial, weak, or ambiguous?

## Hypothesis

Some scenarios will be ready for manual paired runs, while others will need
revision because they either give away the answer or test an edge case before the
core product is clear.

## Method

Review every E-011 scenario before running models:

1. Does the context block give a task-changing signal without solving the task?
2. Could the baseline reasonably miss the issue?
3. Could the context run over-trust the context?
4. Does the scenario map to a real agent-terminal moment?
5. Is the expected behavior observable in output?

## Ratings

- `ready`: run as-is.
- `revise`: keep scenario, improve setup/context/expected behavior.
- `drop`: not useful for the first benchmark.

## Decision

Pending.
