# E-017 Run: Authority Language Split V1

Date: 2026-06-15

Purpose: decide how to render reviewed guidance versus advisory source matches.

## Core Distinction

Reviewed guidance changes how the agent should approach the task.

A source match changes what the agent should consider checking.

That is the whole split.

## Internal Model

| Internal signal | Source state | User-facing section | User-facing tone |
| --- | --- | --- | --- |
| `approved_guidance` | Reviewed and scoped guidance | `Project guidance` | Applies to this task unless contradicted by fresher evidence. |
| `advisory_match` | Relevant source match from an allowed source | `Good to know` | Worth checking; not policy; not full source content. |

## Language Variants

### Variant A: Too Authoritative

```text
Working context

Project guidance
- An approved vault note says this auth flow uses the legacy token convention.
  Why this matters: this applies to auth-service token changes.
  Source: Obsidian folder Engineering/Auth
```

Why it fails:

- It promotes a note into project guidance.
- It makes `approved` sound like truth rather than source permission.
- It invites the agent to obey the note without opening it.

### Variant B: Too Weak

```text
Working context

Good to know
- A note might mention this auth flow.
  Why this matters: it could be related.
  Source: Obsidian folder Engineering/Auth
```

Why it fails:

- It is so vague the agent may ignore it.
- It does not say what action should change.
- It wastes context budget.

### Variant C: Preferred

```text
Working context

Good to know
- A note in the selected Engineering/Auth folder may be relevant to this auth
  flow.
  Why this matters: it may explain a local token rotation convention.
  Source: Obsidian folder Engineering/Auth
```

Why it works:

- `selected folder` communicates user intent without saying the note is approved.
- `may be relevant` preserves uncertainty.
- The source scope is explicit.
- The agent should inspect or verify the note instead of inventing its contents.

## Revised Local Note Fixture

```yaml
signal_type: advisory_match
source_family: local_notes
scope_keys:
  service: auth-service
freshness: fresh
confidence: medium
agent_visibility: visible
source_display: Obsidian folder Engineering/Auth
evidence_summary: A note in the selected Engineering/Auth folder may be relevant to this auth flow.
```

Rendered card:

```text
Working context

Good to know
- A note in the selected Engineering/Auth folder may be relevant to this auth
  flow.
  Why this matters: it may explain a local token rotation convention.
  Source: Obsidian folder Engineering/Auth
```

Expected agent behavior:

- Inspect or ask to inspect the note if the convention matters.
- Do not treat the note as project policy.
- Do not imply private notes or the whole vault were searched.

## Reviewed Guidance Fixture

```yaml
signal_type: approved_guidance
source_family: project_guidance
scope_keys:
  service: auth-service
freshness: fresh
confidence: high
agent_visibility: visible
source_display: approved project guidance, originally from Jira API-482
evidence_summary: Token rotation must preserve compatibility for legacy clients.
```

Rendered card:

```text
Working context

Project guidance
- Token rotation must preserve compatibility for legacy clients.
  Why this matters: this applies to auth-service token changes.
  Source: approved project guidance, originally from Jira API-482
```

Expected agent behavior:

- Incorporate compatibility preservation into design or tests.
- Keep the guidance scoped to auth-service token changes.
- Verify if fresher evidence conflicts.

## Decision

Use `advisory_match` internally for local note and document matches that are
relevant but not reviewed guidance.

Render advisory matches under `Good to know`.

Reserve `Project guidance` for reviewed, scoped guidance only.

Avoid the phrase `approved note` in user-facing context. Use `selected folder`,
`configured source`, or the concrete source name instead.

## Impact On Existing Fixtures

E-016 Fixture 6 should become `advisory_match`, not `approved_guidance`.

This is a product-level distinction that should be made before backend data
modeling.
