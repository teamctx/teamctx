# OpenRouter Smoke V1

Date: 2026-06-15

Scope: first paired run for `primary-01-overlapping-file-change-v1` only.

Models:

- `openrouter-openai-gpt-5.4-mini` (`openai/gpt-5.4-mini`)
- `openrouter-openai-gpt-5.5` (`openai/gpt-5.5`)

Prompt order followed `run-order.md`: baseline first, context second.

## Files

Raw responses and metadata:

- `responses/openrouter-openai-gpt-5.4-mini/primary-01-overlapping-file-change-v1-baseline.md`
- `responses/openrouter-openai-gpt-5.4-mini/primary-01-overlapping-file-change-v1-context.md`
- `responses/openrouter-openai-gpt-5.4-mini/primary-01-overlapping-file-change-v1-baseline.json`
- `responses/openrouter-openai-gpt-5.4-mini/primary-01-overlapping-file-change-v1-context.json`
- `responses/openrouter-openai-gpt-5.5/primary-01-overlapping-file-change-v1-baseline.md`
- `responses/openrouter-openai-gpt-5.5/primary-01-overlapping-file-change-v1-context.md`
- `responses/openrouter-openai-gpt-5.5/primary-01-overlapping-file-change-v1-baseline.json`
- `responses/openrouter-openai-gpt-5.5/primary-01-overlapping-file-change-v1-context.json`

Scores:

- `results/2026-06-15-openrouter-smoke-v1.csv`

## Observed Scores

| Model | Score | Notes |
| --- | ---: | --- |
| `openrouter-openai-gpt-5.4-mini` | +1 | The context answer identified same-file PR risk and asked for the current file or PR diff before editing. Baseline did not surface the collision. |
| `openrouter-openai-gpt-5.5` | 0 | The context answer did not cleanly use the PR evidence, emitted pseudo terminal/tool-call text, and hit the completion cap. |

## Usage

| Model | Variant | Prompt tokens | Completion tokens | Reasoning tokens | Total tokens | Cost |
| --- | --- | ---: | ---: | ---: | ---: | ---: |
| `openrouter-openai-gpt-5.4-mini` | baseline | 42 | 26 | 0 | 68 | 0.0001485 |
| `openrouter-openai-gpt-5.4-mini` | context | 97 | 93 | 0 | 190 | 0.00049125 |
| `openrouter-openai-gpt-5.5` | baseline | 42 | 63 | 12 | 105 | 0.0021 |
| `openrouter-openai-gpt-5.5` | context | 97 | 900 | 664 | 997 | 0.027485 |

Total reported OpenRouter cost: `0.03022475`.

## Product Read

The first real pilot supports the direction, but also exposes a benchmark-design issue:
when the prompt says the model is working in an agent terminal, some chat models may
emit simulated tool activity instead of a concise next-action answer. The benchmark
needs either a stricter answer format or actual agent-runtime execution for command-capable
models.

Immediate lesson: context can prevent a same-file collision, but the benchmark harness
must separate chat-answer behavior from terminal-agent behavior before broad scoring.
