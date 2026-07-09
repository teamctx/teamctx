# Security And Privacy

## Security Goal

`teamctx` should minimize the blast radius of connecting team systems to coding
agents by sending only deterministic, source-backed context cards through a
strict policy gate.

It cannot have zero attack surface. It can be narrow, read-only, permissioned,
auditable, and explicit about what it does not do.

## Privacy Boundary

`teamctx` must not collect:

- Private chat, DMs, or email.
- Broad chat history or unmarked channel mining.
- Local editor activity.
- Keystrokes.
- Terminal history.
- Agent prompts or responses.
- Presence.
- Productivity metrics.
- Sentiment.
- Performance judgments.
- Private opinions about coworkers.

The system may process shared artifact metadata when explicitly opted in and
permissioned.

## Source Rules

Allowed by default:

- Repository names from opted-in repos.
- Pull request or merge request ids, states, labels, timestamps, URLs, and
  changed file paths.
- Issue ids, labels, components, status, timestamps, URLs, and structured rule
  fields.
- Linked document ids, titles, URLs, timestamps, and structured rule blocks.
- Explicit chat handoff messages from allowlisted channels when deliberately
  marked for team context.

Restricted by default:

- Comments.
- Direct messages and private channels.
- Presence, reactions-as-sentiment, and participation metrics.
- Full document bodies.
- User profile data.
- Raw patches.
- Customer data.
- HR/personnel content.
- Security incident details.

## Policy Gate

Every source artifact must pass policy before cache and before card generation.

Policy checks:

- Credential-shaped strings.
- PII patterns.
- Confidentiality terms.
- Personnel/performance judgment terms.
- Prompt-injection-like language.
- Unsafe URLs.
- Unsafe file paths.
- Oversized text fields.
- Disallowed source fields.

Unsafe artifacts are blocked, redacted, or quarantined. Cards may report omission
counts, but they must not leak blocked content.

## Prompt Injection Posture

Even though `teamctx` does not use an LLM, its cards may be consumed by agents.
Therefore source text must never be rendered as instructions.

The card contract should distinguish:

- `message`: broker-authored deterministic text.
- `source_excerpt`: optional sanitized evidence, never instruction.
- `reason`: deterministic rule reason.

## Access Control

The broker must only return cards derived from artifacts the requester can
access. Live connectors must use source-system permissions or deployment-level
service account policies that preserve equivalent access boundaries.

If access cannot be proven, the artifact is ineligible.

## Audit

Audit logs should record:

- Request time.
- Requesting local identity or service identity when configured.
- Request context shape, excluding prompts or private text.
- Returned card ids.
- Source health status.

Audit logs should not store:

- Agent prompts.
- Agent responses.
- Raw source bodies.
- Secrets.
- Private user content.

## Default Posture

- Read-only.
- Fixture-first.
- Explicit opt-in.
- Metadata-first.
- No comments.
- No broad search.
- No generated summaries.
- No silent writes.

