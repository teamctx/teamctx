# E-002 Run: Language Cards V1

Date: 2026-06-15

Purpose: test whether plain user-facing language works better than internal
TeamCtx language for concrete agent-terminal moments.

This is not final UI. These are examples for review.

## Review Instructions

For each example, answer:

1. What happened?
2. Why are you seeing it?
3. What would each action do?
4. Does anything feel like tracking, memory, or enterprise search?
5. Which version is clearer?

## Example 1: Overlapping Work

### Product Language

```text
Needs attention
Another open PR changed src/auth/token.py 11 minutes ago.

Why this matters: you are editing the same file.
Source: GitHub PR #482

Actions: Use now | Ignore | Don't show this PR again
```

### Internal Language

```text
Context card: overlapping_change
Artifact: github_pull_request org/app#482
Reason: path_intersection(src/auth/token.py)
Trust tier: source_evidence
Actions: consume | mute_artifact | mute_source
```

## Example 2: Changed Acceptance Criteria

### Product Language

```text
Needs attention
The linked Jira issue added a compatibility requirement today.

Why this matters: your branch started before the issue changed.
Source: Jira API-482

Actions: Use now | Save for later | Ignore
```

### Internal Language

```text
Context card: changed_acceptance_criteria
Artifact: jira_issue API-482
Reason: issue.updated_at > branch.started_at
Authority: unreviewed_source
Actions: consume | promote | dismiss
```

## Example 3: Stale Process Doc

### Product Language

```text
Verify before relying
The release checklist source is stale.

Why this matters: missing checklist updates should not be treated as no risk.
Source: Confluence Release Checklist

Actions: Check source | Continue without it
```

### Internal Language

```text
Context card: source_stale
Artifact source: confluence
Health: stale
Trust tier: verify_before_relying
Actions: inspect_source | proceed
```

## Example 4: Obsidian Note Match

### Product Language

```text
Good to know
An approved vault note mentions this auth flow.

Why this matters: it may explain the local token rotation convention.
Source: Obsidian folder Engineering/Auth

Actions: Open note | Save for this project | Ignore
```

### Internal Language

```text
Context card: docs_process_note_match
Artifact: obsidian_note Engineering/Auth/token-rotation.md
Authority: advisory_source
Actions: inspect_artifact | promote | dismiss
```

## Example 5: Private Note Omitted

### Product Language

```text
Not shown
Some local vault notes were skipped.

Why this matters: private, personal, or local-only paths are not used for team
context.
Source: Obsidian vault scan

Actions: Review source settings
```

### Internal Language

```text
Omission: policy_blocked_artifact
Artifact source: obsidian
Reason: local_path_part(private|personal|scratch)
Action: inspect_omission
```

## Example 6: Saved Project Guidance

### Product Language

```text
Saved for this project
Legacy token clients must remain compatible.

Why this matters: this applies to auth-service API changes.
Source: approved project guidance, originally from Jira API-482

Actions: Use now | Why am I seeing this? | Suggest update
```

### Internal Language

```text
Reviewed entry: decision/auth-legacy-token-compatibility
Authority: reviewed_knowledge
Scope: repo=auth-service
Actions: consume_authoritative | explain_authority | propose_revision
```

## Example 7: Explicit Chat Handoff

### Product Language

```text
Good to know
Maya marked a handoff for this deployment.

Why this matters: it references the release branch you are working on.
Source: Slack #deployments, marked handoff

Actions: Open message | Use now | Ignore
```

### Internal Language

```text
Artifact: slack_handoff_message
Selector: channel_allowlist + explicit_marker
Identity policy: minimal
Actions: inspect_artifact | consume | dismiss
```

## Example 8: Unsupported Chat

### Product Language

```text
Not shown
Private messages and unmarked chat are not used for working context.

Why this matters: TeamCtx only uses explicit handoffs from approved channels.
Source: chat source settings

Actions: Review source settings
```

### Internal Language

```text
Omission: unsupported_source_scope
Source family: chat
Reason: dm_or_unmarked_channel_message
Actions: inspect_policy
```

## Example 9: Source Unavailable

### Product Language

```text
Needs attention
Jira is unavailable, so issue-related context may be missing.

Why this matters: absence of Jira cards is not a green light.
Source: Jira source health

Actions: Retry source | Continue without it
```

### Internal Language

```text
Context card: source_unavailable
Source instance: jira-cloud-primary
Health: unavailable_no_baseline
Actions: refresh_source | proceed_with_omission
```

## Example 10: Keep For Future

### Product Language

```text
Save for later?
This requirement may apply to future auth work:
"Token rotation must preserve legacy client compatibility."

Source: Jira API-482
Applies to: auth-service

Actions: Save draft | Edit first | Cancel
```

### Internal Language

```text
Promotion candidate
Source artifact: jira_issue API-482
Target type: reviewed_guidance
Scope: repo=auth-service
Actions: create_proposed_entry | edit_promotion_plan | abort
```

## Early CTO Read

Likely stronger language:

- `Needs attention`
- `Good to know`
- `Verify before relying`
- `Not shown`
- `Save for later?`

Likely risky language:

- `Saved for this project`, because it may feel permanent or like storage.
- `Use now`, because it is vague unless the action inserts context into the
  agent session.
- `Save for later`, because it still brushes against memory. It may need
  `Add to project note`, `Save as guidance`, or `Draft guidance`.

Open product questions:

- Does `Use now` mean "show this to the agent," "open the source," or "pin it
  for this session"?
- Should `Save for later` always open an editable draft instead of saving
  directly?
- Should omitted/private source notices appear by default, or only in source
  health/debug views?
