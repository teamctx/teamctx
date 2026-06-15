# E-006 Run: Benchmark Scenarios V1

Date: 2026-06-15

Purpose: define paired agent-task scenarios that can test whether TeamCtx-style
working context improves real agent work.

Each scenario should be runnable two ways:

- baseline: task only
- context: task plus working-context surface

## Scoring

For each paired run, record:

- Correctness: better / same / worse
- Missed constraint: yes / no
- Over-trust: yes / no
- Human intervention needed: yes / no
- Source lookups avoided: count
- Irrelevant context items shown: count
- Notes

## Scenario 1: Overlapping File Change

Task:

```text
Update src/auth/token.py to add token rotation retry handling.
```

Context version:

```text
Working context

Needs attention
- Another open PR changed src/auth/token.py 11 minutes ago.
  Why this matters: you are editing the same file.
  Source: GitHub PR #482
```

Expected improvement:

- Agent checks or mentions overlapping work before editing heavily.
- Agent avoids assuming the local file is the only current source of truth.

Failure mode:

- Agent refuses to work at all.
- Agent treats PR #482 as authoritative without inspecting it.

## Scenario 2: Changed Acceptance Criteria

Task:

```text
Finish the token rotation implementation for auth-service.
```

Context version:

```text
Working context

Needs attention
- The linked Jira issue changed after this branch started.
  Why this matters: acceptance criteria may have changed.
  Source: Jira API-482
```

Expected improvement:

- Agent asks to inspect or account for the changed issue before finalizing.
- Agent avoids declaring completion based only on old assumptions.

Failure mode:

- Agent invents the new acceptance criteria.
- Agent treats "changed" as a specific requirement without source evidence.

## Scenario 3: Stale Process Doc

Task:

```text
Prepare the release checklist updates for today's auth-service release.
```

Context version:

```text
Working context

Verify before relying
- The release checklist source is stale.
  Why this matters: missing checklist updates should not be treated as no risk.
  Source: Confluence Release Checklist
```

Expected improvement:

- Agent does not rely on stale checklist content as current.
- Agent suggests verifying the source or proceeds with clear caveat.

Failure mode:

- Agent ignores stale status.
- Agent over-emphasizes stale status and cannot proceed with any useful work.

## Scenario 4: Saved Guidance Applies

Task:

```text
Change auth-service token rotation behavior for legacy clients.
```

Context version:

```text
Working context

Saved for this project
- Token rotation must preserve compatibility for legacy clients.
  Why this matters: this applies to auth-service token changes.
  Source: approved project guidance, originally from Jira API-482
```

Expected improvement:

- Agent preserves compatibility in design/tests.
- Agent cites the guidance as scoped to auth-service.

Failure mode:

- Agent applies this guidance outside scope.
- Agent treats guidance as a universal company rule.

## Scenario 5: Safety-Blocked Source Change

Task:

```text
Finish auth-service compatibility work from the linked Jira issue.
```

Context version:

```text
Working context

Needs attention
- The linked Jira issue changed after this branch started.
  Why this matters: acceptance criteria may have changed, but part of the issue
  was blocked by safety policy.
  Source: Jira API-482
```

Expected improvement:

- Agent recognizes uncertainty and avoids inventing blocked content.
- Agent asks to open source or continue carefully.

Failure mode:

- Agent guesses the blocked content.
- Agent asks the user to paste secrets or blocked source text.

## Scenario 6: Explicit Chat Handoff

Task:

```text
Continue the deployment work for release/2026-06-15.
```

Context version:

```text
Working context

Good to know
- A deployment handoff was marked for this release branch.
  Why this matters: you are working on release/2026-06-15.
  Source: Slack #deployments, marked handoff
```

Expected improvement:

- Agent checks or accounts for the handoff.
- Agent does not infer broader Slack history.

Failure mode:

- Agent assumes Slack is broadly searchable.
- Agent overweights chat as more authoritative than source-controlled release
  docs.

## Scenario 7: Inaccessible Linked Docs

Task:

```text
Implement the release process update linked from the issue.
```

Context version:

```text
Working context

Source unavailable
- Some linked docs could not be checked with your access.
  Why this matters: missing doc context should not be treated as no doc risk.
  Source: docs source health
```

Expected improvement:

- Agent avoids assuming no doc constraints exist.
- Agent asks for access/source verification if the doc matters.

Failure mode:

- Agent tries to infer inaccessible doc content.
- Warning creates too much anxiety for a low-risk task.

## Scenario 8: Vault Note Advisory Only

Task:

```text
Explain the local token rotation convention before editing auth-service.
```

Context version:

```text
Working context

Good to know
- An approved vault note mentions this auth flow.
  Why this matters: it may explain the local token rotation convention.
  Source: Obsidian folder Engineering/Auth
```

Expected improvement:

- Agent treats the note as advisory and asks to inspect before relying.
- Agent distinguishes vault notes from approved project guidance.

Failure mode:

- Agent treats the vault note as authoritative.
- Agent implies private/personal vault content was searched.

## Benchmark Readiness

Ready enough to run manually with any agent/model after CPO review.

Known gaps:

- Need actual source snippets or fixture artifacts for stronger tests.
- Need a consistent way to measure tokens across agents.
- Need to decide whether the context block is injected into the agent prompt,
  shown to the human, or both.
- Need CPO judgment on whether the cards feel natural before benchmark runs.

## Decision

Advance to manual paired runs after one CPO pass on language and scenario fit.
