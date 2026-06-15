# E-002 Language And Action Test

## Question

Can users understand and control TeamCtx without learning TeamCtx's internal
ontology?

## Hypothesis

Users can act correctly if the product displays ordinary verbs and accepts plain
language intent. These are candidate labels or natural-language actions, not
required command names:

- `Use now`
- `Keep for future`
- `Ignore`
- `Don't show this again`
- `Why am I seeing this?`

Users will get confused or distrustful if the product exposes internal nouns:

- `promotion`
- `artifact`
- `durable context`
- `authority`
- `trust tier`
- `quarantine`

## Method

Create 10 context-card examples from real or realistic work sessions.

For each card, test two versions:

- product language
- internal language

Ask the reviewer:

1. What happened?
2. Why are you seeing this?
3. What would each action do?
4. Would you want this shown automatically next time?
5. Does anything feel like tracking, surveillance, or vague AI memory?

## Pass Criteria

- Reviewers correctly predict action outcomes without explanation.
- Product-language cards feel less creepy than internal-language cards.
- At least one action can be removed or renamed based on confusion.

## Fail Criteria

- Users need docs to understand basic actions.
- Users think they need to type exact TeamCtx phrases.
- `Keep for future` sounds like surveillance or permanent memory.
- Source health is ignored or misunderstood.
- The product needs a glossary before the user can proceed.

## Decision

Pending.
