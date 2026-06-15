# E-011 Manual Benchmark Protocol

## Question

Can a small TeamCtx-style context block improve agent work in paired tasks, and
can we measure the effect without building connectors first?

## Hypothesis

If the product thesis is right, a short context block will improve correctness or
reduce lookup/re-explanation in at least some tasks without causing over-trust.

## Method

Run each scenario twice:

1. Baseline: task prompt only.
2. Context: same task prompt plus a working-context block.

Use the provisional language set from E-010 unless testing a language variant.

## Controls

- Same task wording in baseline and context runs.
- Same model/agent when possible.
- No hidden source access in context run unless the baseline also has it.
- Context block must be short enough to read before work starts.
- Score over-trust explicitly, not just correctness.

## Measurements

- correctness: better / same / worse
- missed constraint: yes / no
- over-trust: yes / no
- source lookup avoided: yes / no / unclear
- human intervention: yes / no
- irrelevant context count
- language confusion: yes / no
- notes

## Pass Criteria

Across 8 paired scenarios:

- Context improves or preserves correctness in at least 6.
- Context causes zero severe over-trust errors.
- At least 3 scenarios avoid a lookup, repeated explanation, or missed caveat.
- Average irrelevant context count is below 1 per task.

## Fail Criteria

- Context makes agents more confident without evidence.
- Context creates more human correction than baseline.
- Agents ignore stale/unavailable warnings.
- Language confusion dominates task performance.

## Decision

Pending.
