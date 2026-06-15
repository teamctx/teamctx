# E-032 Run: OpenRouter Smoke V1

Date: 2026-06-15

Purpose: run the first real paired benchmark scenario against OpenRouter
models and save raw responses plus metadata in the generated packet.

## Scope

- Scenario: `primary-01-overlapping-file-change-v1`
- Models: `openai/gpt-5.4-mini`, `openai/gpt-5.5` via OpenRouter
- Prompt order: baseline first, context second

## Output

- Raw responses under `runs/2026-06-15-e029-primary-benchmark-export/responses/`
- Scores under `runs/2026-06-15-e029-primary-benchmark-export/results/`

## Result

- `openrouter-openai-gpt-5.4-mini`: +1
- `openrouter-openai-gpt-5.5`: 0

## Learning

The smaller model showed the intended product effect: working context caused
the answer to pause for same-file PR evidence before editing. The stronger
model exposed a harness problem by emitting pseudo terminal/tool-call text and
hitting the completion-token cap on the context variant.

Before running the full packet, tighten the benchmark prompt format or run
agent-capable models inside an actual tool harness.
