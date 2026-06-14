# teamctx Product Plan

## Product Identity

Name: `teamctx`

Primary docs site: `teamctx.dev`

## Category

Deterministic ambient context infrastructure for software teams.

This is not an AI assistant, agent runtime, enterprise search engine, memory
system, observability tool, or productivity analytics product.

## Core Idea

Software teams already write down the context they need in shared artifacts:
pull requests, merge requests, issues, acceptance criteria, process docs,
release checklists, architecture records, project notes, and explicit chat handoffs.

The problem is not absence of information. The problem is timing, relevance,
safety, and fragmentation.

`teamctx` connects approved team systems and emits small, source-backed context
cards when current work intersects something the developer or coding agent needs
to know.

The product should feel like:

> `git status`, but for team context.

Not:

> A chatbot that read the company.

## Product Promise

When a developer or coding agent starts work, `teamctx` should answer:

- Is there overlapping work?
- Did a linked issue or acceptance criterion change?
- Did a relevant process doc change?
- Is there a required rule for this file, component, course section, or task?
- Are configured sources unavailable, stale, or incomplete?
- What exact artifact proves each answer?

It should answer without:

- Monitoring people.
- Reading private messages.
- Logging prompts.
- Using an LLM.
- Generating speculative summaries.
- Sending bulk source text into an agent.
- Surfacing sensitive, private, or unsafe content.

## Example Moments

### Overlapping Work

```text
Heads up: open PR #482 changed src/auth/token.py 11 minutes ago.
Reason: same repo and same file path.
Source: https://github.com/org/app/pull/482
```

### Issue-Specific Constraint

```text
Required: learner-facing text for COURSE-123 must not use semicolons.
Reason: linked issue structured rule applies to this course section.
Source: https://jira.example.com/browse/COURSE-123
```

### Process Doc Update

```text
Notice: the release checklist linked from this issue changed after this branch started.
Reason: linked doc updated_at is newer than branch started_at.
Source: https://confluence.example.com/pages/release-checklist
```

### Honest Missing Context

```text
Warning: configured Jira source has no successful refresh baseline.
Reason: source unavailable; missing issue cards should not be treated as no issue risk.
```

## Audience

### Primary

Software teams using coding agents and shared work systems.

### Primary Adopters

- Engineering leaders who want less chat-driven coordination.
- Platform teams responsible for safe agent adoption.
- Developers who regularly work across PRs, issues, docs, and generated content.
- Teams with strict process or content constraints that agents must respect.

### Operators

- Developer experience teams.
- Security engineering teams.
- AI tooling/platform teams.
- Regulated engineering organizations.

## Source Families

`teamctx` is designed for source families instead of one vendor stack.

- Forge review: GitHub pull requests and GitLab merge requests.
- Work tracking: Jira issues and Linear issues.
- Docs/process: Confluence pages and similar governed documentation systems.
- Explicit chat handoff: Slack or Teams-style messages that are allowlisted
  and deliberately marked for team context.

The chat family is intentionally narrow. It is not Slack search, DM mining,
presence tracking, sentiment analysis, or team-activity analytics.

## Product Positioning

`teamctx` is intentionally narrower than Rovo, Glean, Copilot, Augment, or a
generic MCP server.

Those products often optimize for broad access to company knowledge or agent
execution. `teamctx` optimizes for the minimum useful, safe, deterministic
context needed for the current work.

The differentiator is not "AI knows everything."

The differentiator is:

> The right artifact-backed fact appears at the right moment, with a source link,
> a reason, and a safety boundary.

## Product Principles

### 1. Artifact-Only

Observe shared artifacts, not people.

Allowed inputs are approved PRs, MRs, issues, docs, structured rules, labels,
paths, states, timestamps, and source health.

Private messages, editor activity, presence, productivity, sentiment, and
interpersonal commentary are outside the product.

### 2. No LLM In The Broker

The broker is deterministic. It does not infer, summarize, classify, or advise
using a model.

If an agent consumes a card through an optional downstream surface, the card
itself is still produced by rules, relationships, timestamps, and policy checks.

### 3. Context Cards, Not Dumps

The primary output is a compact context card.

Cards are broker-authored facts. They include source, URL, reason, severity,
updated time, and omission metadata.

### 4. Permission Before Relevance

If access cannot be proven, the artifact is ineligible.

The system must never answer "this is relevant" before answering "this user or
deployment is allowed to see it."

### 5. Source Text Is Untrusted

Artifact titles, bodies, comments, and docs are untrusted evidence. They can
contain secrets, sensitive content, or prompt-injection-like text.

They must never become instructions.

### 6. Quiet By Default

Most context should be pull-based. Interruptions are for high-signal cards:
overlapping work, required constraints, changed acceptance criteria, linked doc
updates, source unavailability, and safety blocks.

### 7. Claims Require Proof

No live connector, safety claim, privacy claim, or source support claim is public
without fixtures, tests, and failure-path coverage.

## Non-Goals

- Build an agent.
- Build a chatbot.
- Build enterprise search.
- Build general memory for agents.
- Mine Slack, email, DMs, or private channels.
- Track productivity, presence, or participation.
- Rank people.
- Infer intent from local activity.
- Replace human review.
- Generate summaries from arbitrary prose.
- Send large source bodies into coding agents.

## Core Product Objects

### Artifact

A normalized source-system object.

Examples:

- GitHub pull request.
- GitLab merge request.
- Jira issue.
- Confluence page.
- Structured process rule.
- Fixture artifact.

### Relationship

A deterministic edge.

Examples:

- PR touches file.
- Branch references issue.
- Issue links doc.
- Doc defines rule for component.
- Issue rule applies to course section.
- Artifact changed after branch start.

### Context Card

The primary product output.

Required fields:

```json
{
  "id": "card_...",
  "kind": "overlapping_change",
  "severity": "warning",
  "message": "Open PR #482 changed src/auth/token.py 11 minutes ago.",
  "source": "github",
  "source_url": "https://github.com/org/app/pull/482",
  "reason": "same repo and same file path",
  "applies_to": {
    "repo": "org/app",
    "paths": ["src/auth/token.py"]
  },
  "updated_at": "2026-06-14T16:20:00Z",
  "detected_at": "2026-06-14T16:31:00Z",
  "safety": {
    "text_trust": "untrusted_source",
    "redacted": false
  },
  "omissions": {
    "privacy": 0,
    "safety": 0,
    "budget": 0
  }
}
```

## First Card Kinds

- `overlapping_change`
- `linked_issue_rule`
- `acceptance_criteria_changed`
- `linked_doc_changed`
- `source_unavailable`
- `source_stale`
- `policy_blocked_artifact`

## Fixture-Backed Contract

The fixture-backed contract proves the domain model, safety boundary, card
format, and rules without live API ambiguity.

### Fixture Inputs

A JSON fixture containing:

- Repos.
- Branches.
- Pull requests.
- Issues.
- Docs.
- Structured rules.
- Source health.
- Permissions.

### Fixture Request

```json
{
  "repo": "org/app",
  "branch": "feature/COURSE-123-token-flow",
  "base_branch": "main",
  "branch_started_at": "2026-06-14T15:00:00Z",
  "paths": ["src/auth/token.py"],
  "linked_issue": "COURSE-123",
  "component": "auth",
  "course_section": "intro-js-functions"
}
```

### Fixture Outputs

Deterministic context cards with exact golden-test expectations.

### Fixture CLI

```bash
teamctx status
teamctx cards --fixture docs/fixtures/production-day.json \
  --repo org/app \
  --branch feature/COURSE-123-token-flow \
  --path src/auth/token.py \
  --issue COURSE-123
```

## Implementation Architecture

```text
src/teamctx/
  core/
    artifacts.py
    relationships.py
    cards.py
    rules.py
    policy.py
    relevance.py
    scope.py
  connectors/
    fixtures.py
  cli/
    main.py
  server/
    api.py
```

`teamctx.core` is pure. It has no filesystem, network, subprocess, current-time,
or random behavior. All inputs are explicit.

## Implementation Plan

### Slice 1: Product Contract

Deliver:

- README.
- Product brief.
- Product plan.
- Architecture doc.
- Security/privacy doc.
- Build plan.
- Quality bar.
- ADRs.
- Python package metadata.
- Contract tests.

### Slice 2: Core Schema

Deliver:

- `Artifact`
- `Relationship`
- `ContextCard`
- `RequestContext`
- `SourceHealth`
- `Omissions`
- `PolicyVerdict`

Tests:

- Serialization is stable.
- Required fields are enforced.
- Card ids are deterministic.
- Unsafe enum values fail clearly.

### Slice 3: Policy Gate

Deliver:

- Secret scanning.
- PII review/block rules.
- Prompt-injection-like text detection.
- Unsafe URL/path rejection.
- Field allowlist per artifact type.

Tests:

- Secrets never appear in cards.
- Unsafe source text is redacted or blocked.
- Source text remains evidence, not instruction.

### Slice 4: Relationship Engine

Deliver:

- Same file overlap.
- Same repo overlap.
- Branch-to-issue extraction.
- Issue-to-doc links.
- Rule applicability by repo/path/component/course section.
- Changed-after-branch-start relation.

Tests:

- Relationship derivation is deterministic.
- Weak matches do not produce interrupt cards.
- Missing optional request fields reduce cards safely.

### Slice 5: Card Rules

Deliver:

- Overlapping change cards.
- Linked issue rule cards.
- Acceptance criteria changed cards.
- Linked doc changed cards.
- Source unavailable/stale cards.

Tests:

- Golden card outputs.
- Severity thresholds.
- Provenance required on every card.
- Omission counts preserved.

### Slice 6: Fixture Connector And CLI

Deliver:

- Fixture loader.
- `teamctx cards`.
- `teamctx status`.
- `teamctx inspect`.
- Production-day fixture.

Tests:

- No-network smoke.
- Malformed fixture failures.
- Deterministic output order.

### Slice 7: Local Server

Deliver:

- Read-only local HTTP or stdio API.
- Optional read-only MCP surface.
- `get_context_cards`.
- `get_source_health`.

Constraints:

- No write tools.
- No source mutation.
- No hidden agent behavior.

### Slice 8: First Live Connector

GitHub PR metadata is the first live connector candidate.

Scope:

- Opted-in repos only.
- PR id, title, URL, state, labels, timestamps, changed paths.
- No comments.
- No patches.
- No broad search.

Exit criteria:

- Permission model documented and tested.
- Source-health behavior tested.
- Malicious text fixtures tested.

### Slice 8: Connector Family Expansion

Deliver:

- Linear connector under the work-tracker family contract.
- Slack connector under the explicit chat-handoff family contract.
- Additional docs/process connectors under the docs family contract.
- Conformance tests that prove every connector honors source health,
  permission proof, body policy, identity policy, and omissions.

## Product Decisions To Resolve

- Which release should introduce live connectors after the fixture contract is stable?
- Should `teamctx.dev` be docs-only or include an interactive product demo?
- Which live connector family should follow GitHub: work tracking, docs/process, or explicit chat handoff?
- Should the optional MCP surface be included in the first release or delayed
  after the CLI/card contract is stable?
- Should structured rules use YAML blocks, JSON fields, or source-system custom
  fields first?

## Project Bar

This project is maintained as production-grade infrastructure.

- Apache-2.0.
- DCO.
- Changelog.
- Security policy.
- Code of conduct.
- Strict typing.
- Deterministic tests.
- Fixture-first proof.
- Clear ADRs.
- No product claim without executable proof.

