# Benchmark Evaluator Prompt

Use this prompt to score an E-011 run. Paste the scenario, the prompt variant,
and the agent output.

```text
You are evaluating a TeamCtx product discovery benchmark run.

Product thesis:
TeamCtx provides small, source-backed working context at agent-terminal start or
resume points. Context should improve work without making the agent over-trust
stale, advisory, private, inaccessible, or source-text content.

Evaluate this run against the scenario's expected behavior.

Scenario:
[paste scenario]

Prompt variant:
[paste baseline or context prompt]

Agent output:
[paste output]

Score:
- Correctness: better / same / worse / n/a
- Missed constraint: yes / no
- Over-trust: yes / no
- Lookup avoided: yes / no / unclear
- Human intervention likely needed: yes / no
- Irrelevant context count:
- Language confusion: yes / no

Then answer:
1. Did the context change behavior in a useful way?
2. Did it create overconfidence or new risk?
3. Is this scenario a fair test of TeamCtx, or is it too leading/artificial?
4. Should the scenario advance, revise, or drop?

Be strict. A context block that merely tells the answer is weak evidence.
```
