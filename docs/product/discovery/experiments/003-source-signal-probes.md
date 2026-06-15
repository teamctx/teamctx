# E-003 Source Signal Probes

## Question

Which source families produce high-signal working context for agent-terminal
work, and which ones create noise, privacy risk, or implementation drag?

## Hypothesis

The first useful source order is:

1. local git and repo state
2. GitHub or GitLab review artifacts
3. Jira or Linear work tracking
4. Confluence, Notion, or repo docs
5. Obsidian or Markdown vault notes
6. explicit chat handoffs

Chat should stay last unless the handoff boundary is extremely narrow.

## Method

For each source family, run a no-code probe:

1. Pick 3 real or realistic agent tasks.
2. Manually gather only allowlisted source items.
3. Write the working-context cards those items would generate.
4. Score every card as `helped`, `maybe`, `noise`, or `unsafe`.
5. Record which selector made the item eligible.

## Source Probe Fields

- Source family:
- Source item:
- Selector:
- Permission proof:
- Freshness:
- Card:
- Why shown:
- User action:
- Score:
- Failure mode:

## Pass Criteria

- A source family produces at least 2 high-signal cards across 3 tasks.
- Eligibility can be explained without broad search.
- Unsafe/private items can be omitted without leaking their contents.
- Freshness can be represented honestly.

## Fail Criteria

- The source needs broad search to be useful.
- Most cards are summaries of documents rather than task-changing facts.
- The permission story is unclear.
- The source makes the product feel like monitoring.

## Decision

Pending.
