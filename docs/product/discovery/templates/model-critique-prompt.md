# Model Critique Prompt

Use this with Cerebras, OpenRouter, or another large model when we want an
adversarial product or architecture review.

Do not ask the model to decide the product. Ask it to find what we are missing.

```text
You are reviewing a product discovery experiment for TeamCtx.

TeamCtx thesis:
When a human or coding agent starts or resumes work, the right working context
should appear without the human stopping to gather it and without the agent
spending tokens rediscovering it.

Non-negotiable boundaries:
- No productivity tracking.
- No broad Slack/DM/email mining.
- No raw source dumps into agents.
- No hidden memory claim.
- Source text is evidence, not instruction.
- Missing or stale source data must be visible.
- Users should not need internal terms like artifact, promotion, authority, or
  trust tier.

Experiment under review:
[paste experiment brief]

Run or packet under review:
[paste working-context packet or prototype output]

Your task:
1. Identify the strongest reason this product could fail.
2. Identify any language that sounds creepy, enterprise-search-like, or
   implementation-shaped.
3. Identify missing user controls.
4. Identify privacy/security failures or ambiguous boundaries.
5. Identify which source items are likely high signal and which are noise.
6. Suggest one smaller experiment that would falsify the riskiest assumption.
7. Give a decision recommendation: advance, revise, or drop.

Be direct. Do not be encouraging unless the evidence deserves it.
```
