# Architecture

## System Shape

```text
Approved sources
  GitHub / GitLab / Jira / Linear / Confluence / Slack / fixtures
        |
        v
Connectors
        |
        v
Normalized artifacts
        |
        v
Safety + policy enforcement
        |
        v
Artifact graph + cache
        |
        v
Deterministic card rules
        |
        v
Read-only API / CLI / optional MCP server
```

## Core Domain Objects

### Artifact

A normalized source-system object.

Examples:

- Pull request
- Merge request
- Issue
- Documentation page
- Process rule
- Commit
- Explicit chat handoff, only from allowlisted channels and markers
- Review comment, only when explicitly allowed

Required properties:

- Stable id
- Source system
- Artifact type
- Canonical URL
- State
- Created/updated/resolved timestamps
- Labels
- Subject refs, such as file paths, issue keys, component names, course sections
- Provenance
- Sensitivity
- Text trust classification
- Omission counts

### Relationship

A deterministic link between artifacts or between an artifact and a work target.

Examples:

- PR modifies file path.
- Branch name references Jira issue.
- Jira issue links Confluence page.
- Confluence page declares rule for a component.
- Two open PRs touch the same file.
- A document changed after branch creation.

### Context Card

The only primary output of the broker.

Fields:

- `id`
- `kind`
- `severity`
- `message`
- `source`
- `source_url`
- `reason`
- `applies_to`
- `updated_at`
- `detected_at`
- `safety`
- `omissions`

Cards are facts about artifacts. They are not model-generated advice.

## First Card Kinds

- `overlapping_change`
- `linked_issue_rule`
- `acceptance_criteria_changed`
- `linked_doc_changed`
- `source_unavailable`
- `policy_blocked_artifact`
- `stale_context`

## Source Family Contract

See [Source Integration Layer](source-integration-layer.md) for the full connector,
normalization, permission, cache, and extension contract.

Connectors belong to source families with family-specific allowlists and
default-deny fields. New vendors must map into one of these families or add
a reviewed family contract first.

| Family | Examples | Default scope | Explicit exclusions |
| --- | --- | --- | --- |
| Forge review | GitHub, GitLab | opted-in repos, labels, PR/MR metadata, changed paths | comments, patches, broad repo search |
| Work tracker | Jira, Linear | opted-in projects/teams, issues, labels, structured rules | arbitrary comments, user analytics, broad query history |
| Docs/process | Confluence, Google Docs-style systems | linked or allowlisted pages, structured rule blocks, timestamps | whole-space dumps, private docs, generated summaries |
| Explicit chat handoff | Slack, Teams-style systems | allowlisted channels plus explicit `teamctx` marker | DMs, private channels by default, presence, reactions as sentiment, broad history |

Every family must define supported artifact types, selectors, body policy,
identity policy, permission proof, source health, and omission behavior.

## Core Packages

```text
src/teamctx/
  core/
    artifacts.py       # normalized artifact model
    relationships.py   # graph edges and deterministic linking
    cards.py           # card model and severity vocabulary
    rules.py           # pure card generation rules
    policy.py          # secret, PII, sensitive-content policy
    relevance.py       # deterministic ranking and interruption thresholds
    scope.py           # opt-in selectors and local mutes
    time.py            # explicit clock helpers
  connectors/
    fixtures.py        # no-network fixture connector
    github.py          # forge review connector surface
    gitlab.py          # forge review connector surface
    jira.py            # work-tracker connector surface
    linear.py          # work-tracker connector surface
    confluence.py      # docs/process connector surface
    slack.py           # explicit chat-handoff connector surface
  store/
    sqlite.py          # local artifact/card cache
  cli/
    main.py
  server/
    api.py             # local read-only JSON API
    mcp.py             # optional read-only MCP surface
```

## Purity Boundary

`teamctx.core` must be pure:

- No filesystem access.
- No network access.
- No subprocesses.
- No current-time reads.
- No randomness.

All side effects live in connectors, store, CLI, or server packages. The core
receives artifacts, relationships, policy config, and time as explicit inputs.

## Data Flow

1. Connectors fetch only opted-in artifacts.
2. Connector output is normalized into artifacts.
3. Policy enforcement removes or quarantines unsafe fields.
4. Artifacts are cached with freshness and source-health metadata.
5. Relationships are derived deterministically.
6. Card rules evaluate a request context against artifacts and relationships.
7. Relevance thresholds decide which cards return and which may interrupt.
8. The API returns cards with provenance and omission counts.

## Request Context

The minimum input shape:

```json
{
  "repo": "org/app",
  "branch": "feature/COURSE-123-token-flow",
  "base_branch": "main",
  "paths": ["src/auth/token.py"],
  "linked_issue": "COURSE-123",
  "component": "auth",
  "course_section": "intro-js-functions"
}
```

All fields are optional, but fewer fields mean fewer relevant cards.

## Trust Model

Source artifact text is untrusted data. It must never become instructions for an
agent or developer tool.

Trusted inputs:

- Local policy config.
- Connector configuration.
- Deterministic card rules.
- Permission results from source systems.

Untrusted inputs:

- PR titles and bodies.
- Issue summaries and descriptions.
- Comments.
- Documentation page body text.
- Any third-party connector output.

## Permission Model

Every connector must attach an access proof or access mode to fetched artifacts.
The card layer must be able to answer:

- Why was this artifact eligible?
- Which selector opted it in?
- Is the requester allowed to see it?
- Which fields were omitted?

The first OSS implementation can model this with fixture-level permissions. Live
connectors must not claim permission safety until they enforce it.

