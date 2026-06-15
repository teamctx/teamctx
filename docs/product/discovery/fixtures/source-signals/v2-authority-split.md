# Source Signal Fixtures V2: Authority Split

Date: 2026-06-15

Purpose: revise the E-016 local note fixture after E-017 separated advisory
matches from reviewed project guidance.

## Revised Signal Types

```yaml
signal_type: collision | changed_since_start | stale_source | unavailable_source | blocked_source | approved_guidance | advisory_match | explicit_handoff | runtime_state
```

## Advisory Match

Use for relevant source matches from selected or configured sources when the
source has not been reviewed into project guidance.

Rendered under:

```text
Good to know
```

Agent behavior:

- Inspect or verify if relevant.
- Do not obey as guidance.
- Do not infer source contents beyond the card.

## Approved Guidance

Use only for reviewed, scoped guidance.

Rendered under:

```text
Project guidance
```

Agent behavior:

- Incorporate into the task when in scope.
- Keep scope boundaries.
- Verify if fresher evidence conflicts.

## Revised Fixture: Local Notes

Source input:

- Source family: local notes.
- Source instance: selected Obsidian folder `Engineering/Auth`.
- Scope: auth token rotation.
- Raw signal: a selected folder contains a note that may be relevant to this
  auth flow.

Normalized signal:

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

Working context card:

```text
Working context

Good to know
- A note in the selected Engineering/Auth folder may be relevant to this auth
  flow.
  Why this matters: it may explain a local token rotation convention.
  Source: Obsidian folder Engineering/Auth
```

Should not show:

- `approved note` as user-facing language.
- Private vault matches.
- Note body by default.
- The note as project guidance unless reviewed.

Expected agent behavior:

- Treat the note as a source to inspect or verify.
- Avoid inventing the convention.
- Avoid implying broad vault ingestion.
