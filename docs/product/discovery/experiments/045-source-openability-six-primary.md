# E-045: Source-Openability Six Primary

Date: 2026-06-16

## Question

Does the `status_open` source-routing shape still work across the full primary
benchmark slice after tightening quality scoring for collision behavior and
validation?

## Why This Matters

E-044 was only a two-scenario smoke test. The sprint needs a larger answer
before the implementation moves toward a live Git-host metadata probe.

The product default under test is:

- compact source status reaches the agent by default;
- source bodies are not placed in the workspace by default;
- allowed source bodies can be opened one at a time by explicit action;
- blocked, stale, and unavailable source bodies do not print text.

## Method

Run the six primary fixtures through Claude Code with:

- variant: `context`
- source access: `status_open`
- model: Sonnet
- output: `docs/product/discovery/runs/2026-06-16-e045-source-openability-six-primary-v1/`

The scorer was tightened before this run:

- validation only counts changed tests or validation-shaped Bash commands;
- source-opening commands no longer count as validation;
- the collision scenario has an explicit collision behavior field:
  `preserved_api`, `changed_api`, `blocked`, `unclear`, or `n/a`.

## Result

E-045 produced no failures:

- 4 pass
- 2 review
- 0 fail
- reported total cost: `0.670089`

The collision scenario scored `review` at `8/9`: it preserved the existing API
and added retry behavior through a new helper, but did not run validation.

The changed-acceptance-criteria scenario scored `pass` at `7/7`: it opened the
available Jira source, used the changed criteria, and ran tests.

The stale, blocked, and inaccessible-source scenarios scored pass. The
project-guidance scenario scored `review` because the agent blocked on an
undefined retry window instead of inventing a value; that may be the right
product behavior, but the current scorer still expects implementation evidence.

## Decision

Keep `status_open` as the current product default candidate for the sprint.

Proceed into Core Contract V0 with this contract:

- source status is default-visible when relevant;
- source body opening is explicit, policy-gated, and source-family-specific;
- missing or blocked source bodies can justify caution, but should not become
  generic failure noise;
- collision behavior must preserve the existing API, block, or clearly route to
  review when source body detail is unavailable.

## Follow-Ups

- Decide whether a blocked response caused by missing required detail should be
  pass or review in project-guidance scenarios.
- Add a comparison artifact for E-045 against E-043 after deciding whether old
  runs should be rescored under the stricter scorer.
- Move the next implementation step to Core Contract V0.
