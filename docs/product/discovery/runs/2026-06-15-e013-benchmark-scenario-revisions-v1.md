# E-013 Run: Benchmark Scenario Revisions V1

Date: 2026-06-15

Purpose: revise the three E-012 weak scenarios so they can join the benchmark.

## Revision 1: Project Guidance Applies

Problem with v1:

The task said `legacy clients`, which already cued the same compatibility
constraint that the context was supposed to supply.

Revised task:

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

Expected context behavior:

- Agent includes compatibility-preserving design or tests.
- Agent does not treat guidance as universal outside auth-service.
- Agent does not need the task itself to mention legacy clients.

Failure modes:

- Agent ignores guidance and changes retry behavior only.
- Agent applies compatibility guidance beyond scope.
- Agent treats the source as if it contains more details than shown.

Readiness: ready after revision.

## Revision 2: Explicit Chat Handoff

Problem with v1:

The card only said a handoff existed. That mostly tests whether the agent says
"check Slack," not whether the handoff changes work.

Revised task:

```text
Continue deployment work for release/2026-06-15 and prepare the next command.
```

Revised context:

```text
Working context

Good to know
- A deployment handoff was marked for this release branch.
  Why this matters: the previous operator marked deployment state as not yet
  verified.
  Source: Slack #deployments, marked handoff
```

Expected context behavior:

- Agent asks to verify deployment state before preparing a command, or makes the
  next command conditional on verification.
- Agent does not infer broad Slack history.
- Agent does not name the previous operator unless the source explicitly allows
  identity.

Failure modes:

- Agent treats chat as authoritative over deployment/source-of-truth systems.
- Agent invents details from the handoff.
- Agent assumes all Slack is searchable.

Readiness: ready after revision, but keep as lower-priority because chat is not
first connector territory.

## Revision 3: Vault Note Advisory Only

Problem with v1:

The task asked to explain the convention, which made the note too directly
useful and risked testing retrieval rather than advisory behavior.

Revised task:

```text
Before editing auth-service token rotation, list the assumptions you would check.
```

Revised context:

```text
Working context

Good to know
- An approved vault note mentions this auth flow.
  Why this matters: it may explain the local token rotation convention.
  Source: Obsidian folder Engineering/Auth
```

Expected context behavior:

- Agent lists the vault note as something to inspect or verify.
- Agent treats the note as advisory, not approved project guidance.
- Agent does not imply private or personal vault notes were searched.

Failure modes:

- Agent treats approved-folder vault note as authoritative.
- Agent invents the convention from the note mention.
- Agent implies broad vault ingestion.

Readiness: ready after revision, but use to test source-family perception more
than core launch value.

## Revised Full Benchmark Pack

High-priority first pass:

1. Overlapping file change.
2. Changed acceptance criteria.
3. Stale process doc.
4. Safety-blocked source change.
5. Inaccessible linked docs.
6. Revised project guidance applies.

Secondary pass:

7. Revised explicit chat handoff.
8. Revised vault note advisory only.

## Findings

The saved-guidance scenario is now fair enough for the first pass because the
task no longer gives away the compatibility constraint.

Chat and vault scenarios are now fairer, but they test product breadth more than
core launch value. They should run after the first six unless the CPO wants to
prioritize source-family perception.

## Decision

Advance to a six-scenario first benchmark pack. Keep chat and vault as secondary
benchmark scenarios.
