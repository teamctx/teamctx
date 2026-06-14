# Product Brief

## One-Line Description

`teamctx` gives developers and coding agents the right shared team context at
the moment it matters, without monitoring people and without using generative AI.

## Problem

Engineering teams coordinate through artifacts: pull requests, issues, commits,
review comments, work-tracker records, process docs, release notes, project
records, and explicit chat handoffs. The important facts are present, but they are fragmented across systems and rarely surfaced at
the exact moment a developer needs them.

This creates repeated failure modes:

- A developer edits a file while another pull request is already changing it.
- An agent generates content that violates a note in the linked issue.
- A process document changed, but the person doing the work does not know.
- A team has to ask in chat for context that already exists in a system of record.
- Agents either get too little context or unsafe bulk dumps of irrelevant text.

## Product Vision

`teamctx` is an ambient context layer for teams.

It observes approved shared artifacts, normalizes them, applies strict safety and
privacy policy, and emits concise context cards when a repository, branch, file,
issue, component, or document relationship makes the information relevant.

The product should feel like:

> `git status`, but for team context.

Not:

> A chatbot that read everything.

## Primary Users

- Developers using coding agents.
- Tech leads coordinating overlapping work.
- Documentation and course authors whose work is governed by issue-specific
  constraints.
- Engineering managers who want less chat-driven coordination without adding
  surveillance.
- Security-conscious platform teams that need deterministic behavior and
  auditable context delivery.

## Core Experience

The user should not have to search manually most of the time. `teamctx` should
surface high-signal context when the active work intersects approved artifacts.

Examples:

- "Open PR #482 changed this same file 11 minutes ago."
- "The linked Jira issue added a required content constraint today."
- "The Confluence release checklist changed after this branch was created."
- "Configured source inputs are unavailable; do not treat missing context as
  confirmation that there are no conflicts."

The user can also ask:

```bash
teamctx cards --repo org/app --branch feature/foo --path src/auth/token.py
```

or through a read-only local server/MCP tool:

```json
{
  "repo": "org/app",
  "branch": "feature/foo",
  "paths": ["src/auth/token.py"],
  "linked_issue": "COURSE-123"
}
```

## Source Families

`teamctx` is designed around source families rather than a single vendor stack:

- Forge review: GitHub pull requests and GitLab merge requests.
- Work tracking: Jira issues and Linear issues.
- Docs/process: Confluence pages and similar governed documentation systems.
- Explicit chat handoff: allowlisted Slack channels or similar chat systems, only
  when messages are deliberately marked for team context.

Chat connectors are not workplace monitoring. They must not ingest DMs, private
channels by default, broad history, presence, reactions as sentiment, or
participation analytics.

## Product Principles

### Artifact-Only

The system observes shared artifacts, not people. It can use visible artifact
fields such as author, reviewer, assignee, labels, timestamps, paths, and links
only when those fields are already visible to the requesting user and needed for
the card.

### Deterministic

The context broker does not use an LLM. Card generation comes from explicit
rules, relationship graphs, timestamps, and source metadata.

### Source-Backed

Every card must include provenance: source system, source URL, updated time, and
the rule/reason that caused the card to appear.

### Permission-Aware

The broker must never show a card derived from an artifact the requester cannot
access. Permission checks are part of the retrieval contract, not a UI feature.

### Minimal

Return context cards, not documents. Large bodies stay out of the primary
channel. Raw source text is treated as untrusted evidence.

### Quiet

Interruptions are reserved for high-signal events: overlapping work, changed
acceptance criteria, linked policy changes, safety issues, unavailable sources,
or explicit required rules.

### Safe By Construction

Secrets, sensitive data, private commentary, prompt-injection-like text, and
people judgments must be blocked or quarantined before cards are emitted.

## Non-Goals

- No LLM.
- No agent runtime.
- No productivity analytics.
- No presence tracking.
- No enterprise search engine.
- No arbitrary company-knowledge summarization.
- Mine Slack broadly, email, private messages, or local editor activity.
- Infer productivity, presence, sentiment, or interpersonal dynamics.
- Replace Jira, Confluence, GitHub, GitLab, or human review.
- Generate recommendations from opaque model reasoning.

## Success Criteria

The project succeeds when a team can opt in a small set of repos, issues, and
docs, then get accurate context cards that prevent duplicated work and missed
constraints without adding surveillance or noise.

Early measurable signals:

- Cards are traceable to source artifacts.
- Rules are explainable in tests.
- Fixture-backed production-day simulations are deterministic.
- False-positive interruptions are rare.
- Missing source health is represented honestly.
- No card contains secrets, private commentary, or unsourced claims.

