# E-015 Run: Source Strategy V1

Date: 2026-06-15

Purpose: choose the first source families for TeamCtx working context and avoid
turning the product into monitoring, search, or memory theater.

## Principle

Do not start from connectors. Start from signals.

A connector is justified only when it can produce a signal that changes what the
agent should do next in the current task.

## Source Signal Types

| Signal | Meaning | Example user-visible context |
| --- | --- | --- |
| `collision` | Another active or recent work item touches the same work surface. | Another open PR changed this file recently. |
| `changed_since_start` | A source changed after the branch, task, or session began. | The linked issue changed after this branch started. |
| `stale_source` | A configured source could not be refreshed or is too old. | The release checklist source is stale. |
| `unavailable_source` | The product knows a relevant source exists but cannot inspect it. | Some linked docs could not be checked with your access. |
| `blocked_source` | A relevant source was withheld by safety policy. | Part of the issue was blocked by safety policy. |
| `approved_guidance` | Reviewed project guidance applies to this task scope. | Token rotation must preserve compatibility for legacy clients. |
| `explicit_handoff` | A human intentionally marked context for continuation. | A deployment handoff was marked for this release branch. |
| `runtime_state` | Build, test, deploy, or incident state changes the next action. | The latest deploy job failed after tests passed. |

## Source Family Matrix

| Source family | Examples | Best first signals | Decision | Notes |
| --- | --- | --- | --- | --- |
| Local workspace | Git repo, branch, dirty tree, recent commits | `collision`, `changed_since_start`, `runtime_state` via local artifacts | launch | This is the native habitat. It should work even before SaaS connectors. |
| Git hosting | GitHub, GitLab | `collision`, PR/MR state, review changes, linked issue references | launch | High-value because agents already work from branches and files. Use metadata first, content second. |
| Issue trackers | Jira, Linear, GitHub Issues, GitLab Issues | `changed_since_start`, scope, blockers, linked artifacts | launch | This is where acceptance criteria shift. Must avoid inventing criteria. |
| Docs and wikis | Confluence, Notion, Google Docs, repo docs | `stale_source`, `unavailable_source`, scoped runbook hints | launch with narrow scope | Include configured project docs and linked docs first. Avoid broad workspace search. |
| CI and deploy systems | GitHub Actions, GitLab CI, Buildkite, CircleCI, deployment tools | `runtime_state`, failing jobs, pending deploy verification | probe | Strong signal, but needs careful scoping so it does not become dashboard noise. |
| Approved local notes | Obsidian, Markdown vaults, Logseq, Dendron | advisory hints, `approved_guidance` candidates | probe | Useful for solo/team practices only with allowlisted folders. Advisory by default. |
| Chat handoffs | Slack, Teams, Discord | `explicit_handoff` only | probe later | Valuable, but dangerous if it looks like broad chat mining. Marker-based only. |
| Incident systems | PagerDuty, Opsgenie, Statuspage | `runtime_state` for active incidents | later | Potentially valuable for service work, but not needed for the core benchmark. |
| Email | Gmail, Outlook | maybe explicit handoff, rarely scoped | exclude for first product | Too private, too broad, too hard to explain cleanly. |
| Calendar | Google Calendar, Outlook Calendar | release windows, freezes | later | Useful only when explicitly connected to project/release scope. |
| Personal notes by default | private vaults, scratch files, journals | none by default | exclude | Can be included only through explicit allowlisted folders. |
| Broad drive search | Google Drive, Dropbox, SharePoint | vague document matches | exclude for first product | Too noisy unless entered through configured docs, linked docs, or approved guidance. |
| Activity analytics | time tracking, presence, keystrokes | productivity signals | exclude | This violates the product trust boundary. |

## First Product Source Set

The first product should support this source set conceptually:

1. Local workspace and git metadata.
2. Git hosting metadata: GitHub and GitLab.
3. Issue tracker metadata: Jira first if already present in team workflows;
   Linear/GitHub/GitLab issues as the same source family.
4. Configured docs and linked docs: Confluence, Notion, Google Docs, and repo
   docs through a narrow project scope.
5. Approved local notes as an opt-in folder source: Obsidian and plain Markdown
   first, with Logseq/Dendron as same-family later.

CI/deploy should be the first probe after that, because runtime state can change
the next action sharply.

Chat should not be in the launch set unless the only supported behavior is an
explicit handoff marker in an allowlisted channel.

## Obsidian And Similar Products

Obsidian should not be treated as a magical memory source. It is a local Markdown
source with user-controlled folders.

Adjacent source products worth treating as the same family:

- Plain Markdown folders.
- Logseq graph folders.
- Dendron workspaces.
- Repo-hosted docs.

Products that are adjacent but should enter through docs scope, not note scope:

- Notion.
- Confluence.
- Google Docs.
- SharePoint.

The important distinction is not the app. It is whether the user intentionally
allowed the folder, space, page tree, or linked artifact to influence agent work.

## User-Facing Model

Do not ask users to configure a memory system.

Ask them to choose work sources:

- Code and reviews.
- Issues and planning.
- Project docs.
- Approved notes.
- Builds and releases.
- Marked handoffs.

The product should translate these into working context automatically.

## Product Decisions

- Source setup should say what TeamCtx will and will not use.
- Every source card needs a `Show why` path.
- Sources can produce absence or uncertainty, not only content.
- A stale or inaccessible source is context, but it is not guidance.
- Chat is not a source family at launch unless handoff-only.
- Personal knowledge tools are allowed only as explicit, scoped, approved note
  sources.

## Open Questions

- Is Jira the default issue tracker for first experiments, or should we keep the
  family generic until we know the first users?
- Should CI/deploy state be in the first benchmark before chat and vault?
- What does an approved local note folder look like in setup without sounding
  like surveillance?
- Does `Project guidance` come only from explicit review, or can repeated source
  evidence suggest a draft?
- Should docs/wikis produce direct guidance, or only stale/unavailable/linked-doc
  caveats until reviewed?

## Decision

Use a source-signal model for product planning. The launch product is not a set
of integrations; it is a small set of context signals sourced from the places
agents already touch during work.

Recommended next experiment: create source fixtures for the launch/probe source
families and verify that each can produce at least one useful working-context
card without leaking private or broad search content.
