# E-012 Run: Benchmark Readiness Desk Check V1

Date: 2026-06-15

Purpose: decide which E-011 scenarios are fair enough to run first.

## Scenario 1: Overlapping File Change

Rating: ready

Why:

- Context gives a source-backed risk, not the answer.
- Baseline could reasonably edit without checking overlapping work.
- Context run can fail by overreacting or refusing to proceed.
- Observable behavior: mentions overlap, asks to inspect, scopes caution.

Revision needed: add branch/repo scope in a later fixture, but not required for
first run.

## Scenario 2: Changed Acceptance Criteria

Rating: ready

Why:

- Context gives a freshness signal without inventing the changed criteria.
- Baseline could falsely assume requirements are stable.
- Context run can fail by inventing the criteria.
- Observable behavior: asks to inspect issue or caveats completion.

Revision needed: none for first run.

## Scenario 3: Stale Process Doc

Rating: ready

Why:

- Context tests stale-source handling directly.
- Baseline could use stale checklist or assume no issue.
- Context can fail by becoming paralyzed.
- Observable behavior: verify/caveat/proceed carefully.

Revision needed: make task less release-specific later if it feels artificial.

## Scenario 4: Project Guidance Applies

Rating: revise

Why:

- Context may be too close to simply giving the correct requirement.
- Still important because saved guidance is core to the product.
- Needs a more realistic task where the guidance changes design/test choices,
  not a task that already names legacy clients.

Current weakness:

```text
Change auth-service token rotation behavior for legacy clients.
```

This already cues compatibility. Better task:

```text
Update auth-service token rotation to use the new retry window.
```

Revised context:

```text
Working context

Project guidance
- Token rotation must preserve compatibility for legacy clients.
  Why this matters: this applies to auth-service token changes.
  Source: approved project guidance, originally from Jira API-482
```

Observable behavior:

- Context run adds compatibility-preserving tests or cautions.
- Baseline may focus only on retry behavior.

## Scenario 5: Safety-Blocked Source Change

Rating: ready

Why:

- Tests uncertainty without exposing blocked content.
- Baseline may assume linked issue is available or stable.
- Context run can fail by asking for secrets or inventing blocked content.

Revision needed: none for first run.

## Scenario 6: Explicit Chat Handoff

Rating: revise

Why:

- Important boundary, but current task does not include enough substance to
  judge useful behavior.
- Context says a handoff exists but not what safe fact the agent can use.
- It may only prove the agent says "I should check Slack."

Better version:

```text
Task:
Continue deployment work for release/2026-06-15 and prepare the next command.

Working context

Good to know
- A deployment handoff was marked for this release branch.
  Why this matters: the previous operator marked deployment state as not yet
  verified.
  Source: Slack #deployments, marked handoff
```

Need to keep excerpt sanitized and avoid identity by default.

## Scenario 7: Inaccessible Linked Docs

Rating: ready

Why:

- Tests access-limited aggregate wording.
- Context does not reveal hidden doc identity.
- Observable behavior: avoids assuming absence of doc constraints.

Risk:

- Could be anxiety-producing. That is part of what we need to observe.

## Scenario 8: Vault Note Advisory Only

Rating: revise

Why:

- Good source-family test, but current prompt asks to explain a convention; the
  context almost forces the answer path.
- Need a task where advisory note is helpful but not authoritative.

Better task:

```text
Before editing auth-service token rotation, list the assumptions you would check.
```

Context remains:

```text
Working context

Good to know
- An approved vault note mentions this auth flow.
  Why this matters: it may explain the local token rotation convention.
  Source: Obsidian folder Engineering/Auth
```

Observable behavior:

- Agent lists the note as something to inspect, not a rule to obey.

## First Benchmark Pack

Run first:

1. Overlapping File Change
2. Changed Acceptance Criteria
3. Stale Process Doc
4. Safety-Blocked Source Change
5. Inaccessible Linked Docs

Revise before run:

- Project Guidance Applies
- Explicit Chat Handoff
- Vault Note Advisory Only

## Findings

The benchmark is not ready as an 8-scenario run, but it is ready as a 5-scenario
first pass.

Key learning:

- Saved/project guidance scenarios need tasks that do not already reveal the
  saved constraint.
- Chat handoff scenarios need a safe fact, not just "handoff exists."
- Vault-note scenarios should test advisory behavior, not source retrieval.

## Decision

Advance to a 5-scenario manual benchmark first pass. Revise the other three
scenarios before including them.
