# TeamCtx Product Discovery

This replaces the Ambara-first build plan as the active product path.

Ambara is now an R&D asset: reviewed guidance, source safety, freshness,
authority labels, and durable context mechanics. TeamCtx is the product surface
we are trying to prove.

## Product Thesis

When a human or coding agent starts or resumes work, the right working context
should appear without the human stopping to gather it and without the agent
spending tokens rediscovering it.

The context must be:

- timely enough to change the work
- sourced enough to trust or verify
- small enough to read
- permissioned enough to be safe
- plain enough that users do not need TeamCtx vocabulary

## Product Shape We Are Testing

TeamCtx is not a chatbot, memory product, enterprise search system, or activity
tracker. It is working context for agent-terminal work.

The labels below are candidate words the product might display or use for
actions. They are not commands users are expected to type, and they are not
vocabulary users should have to learn. If the product requires a user to know
these terms, the experiment fails.

Candidate visible language:

- `Heads up`
- `Use now`
- `Keep for future`
- `Saved guidance`
- `Source stale`
- `Not used`
- `Why am I seeing this?`

In a real terminal experience, context should usually appear automatically at
start or resume. User control should be plain language, such as "ignore this" or
"save this for later," not an ontology.

Internal-only language:

- `artifact`
- `promotion`
- `authority`
- `trust tier`
- `durable context`
- `source evidence`
- `quarantine`

## Discovery Rules

- Do not build broad integrations until a manual experiment proves the source is
  useful.
- Do not introduce a product noun when a user verb can carry the action.
- Do not make users type or memorize discovery labels.
- Do not preserve everything. Preserve what reduces future interruption.
- Do not treat source text as instruction.
- Do not hide source health. Missing context is itself context.
- Do not claim support for a source without selectors, permission proof,
  freshness behavior, omission behavior, and malicious-text fixtures.

## Source Families

| Family | Initial sources | Discovery question |
| --- | --- | --- |
| Code and review | GitHub, GitLab, local git | Does this prevent duplicate or conflicting work? |
| Work tracking | Jira, Linear | Does this catch changed scope and acceptance criteria? |
| Docs and process | Confluence, Notion, repo Markdown | Do governed docs produce timely cards without dumping prose? |
| Vault notes | Obsidian, Logseq, Markdown folders | Can approved notes become useful working context without feeling creepy? |
| Explicit handoff | Slack, Teams-style marked messages | Can chat help without becoming chat mining? |
| Durable guidance | TeamCtx saved guidance, Ambara primitives | Can selected context help future work without becoming "AI memory"? |

## Experiment Backlog

| ID | Experiment | Decision it informs |
| --- | --- | --- |
| E-001 | Concierge working context | Whether the core packet helps real agent sessions before automation. |
| E-002 | Language and action test | Which labels users understand without training. |
| E-003 | Source signal probes | Which sources are worth first-class connector investment. |
| E-004 | Saved guidance loop | Whether "Keep for future" produces useful future context. |
| E-005 | Security and privacy red-team | Whether the product fails closed without becoming unusable. |
| E-006 | Agent consumption benchmark | Whether context reduces tokens/time/misses without over-trust. |

## Decision Gates

After each experiment, record one of:

- `advance`: build the next narrow prototype
- `revise`: keep the thesis but change shape, language, or source boundary
- `drop`: stop investing in this path

No experiment graduates on vibes alone. Each needs observed examples, failure
cases, and a clear next decision.

## Current Status

Active experiment: [E-001 Concierge Working Context](experiments/001-concierge-working-context.md)
