# Spec: source breadth: GitLab, Jira, Confluence (Phase 4)

## Status
Revision 1, proposed by the CTO 2026-07-03; goes through a codex adversarial spec review
before build. Grounded in live read-only API recon of a real GitLab account and a real
Atlassian Cloud instance (credentials live in the operator's environment, never in the repo;
no instance names or captured payloads may enter fixtures; tests use synthetic payloads
shaped like the observed responses).

## Goal
The four checks become source-plural without the core learning anything new: GitLab as a
second forge (collision + gate), Jira as a second issue tracker (criteria), Confluence as the
first remote docs source (superseded docs). Each connector proves the SAME honest-coverage
behavior GitHub proved (no token, unreachable, malformed payload, truncation, pending all
route to explicit non-fresh statuses) before it counts as supported. The broker, evaluator,
kinds registry, and render change only where a fact is genuinely provider-shaped (issue ref
format, source_display, open hints).

## Non-goals
No new card kinds. No cross-provider identity resolution. No webhooks or polling daemons
(work-start remains a moment-in-time read). No write access of any kind.

## 1. Configuration and identity (the seam everything hangs on)

`ProjectConfig.work_start` (v0, additive, extra=forbid preserved):

```python
class JiraConfig(StrictConfigModel):
    base_url: str                    # e.g. https://<site>.atlassian.net
    # project scoping is implicit: linked issue refs (PROJ-123) name their project

class ConfluenceConfig(StrictConfigModel):
    base_url: str                    # same Atlassian site; /wiki is appended by the connector
    space_key: str                   # the declared docs space (the reliance declaration)

class WorkStartConfig(StrictConfigModel):
    repo: str | None = None          # forge repo slug (owner/name or group/project)
    forge: Literal["github", "gitlab"] = "github"
    docs_root: str | None = None     # local docs (unchanged)
    jira: JiraConfig | None = None       # None = issue tracker is the forge's (GitHub Issues)
    confluence: ConfluenceConfig | None = None  # None = docs are local only
```

Pinned semantics: ONE forge per repo (the repo is hosted somewhere); the issue tracker MAY
differ from the forge (GitHub repo + Jira issues is a mainstream enterprise reality and the
primary validation combo); docs may be local, Confluence, or both (both sets scan; each is
its own coverage entry in the docs family).

**Repo identity generalizes:** `parse_github_repo` gains a sibling `parse_gitlab_repo`
(gitlab.com host; groups mean the path may have MORE than two segments: `group/sub/project`
is valid and preserved) and a dispatcher `parse_forge_repo(value, forge)` used by ONE
provider-aware `resolve_forge_repo(explicit, config_repo, detected, forge)`; the existing
`resolve_github_repo` becomes the github case of it. `detect_repo` becomes host-aware the
same way onboard's detection already is: the origin host SELECTS the forge (github.com ->
github, gitlab.com -> gitlab, anything else -> honest absence) and onboard writes the
detected `forge` into the config. The runtime and onboard keep sharing one resolver (the
split-brain refusal extends to the forge field).

**Tokens (per-actor, never in config):** GitLab: `GITLAB_TOKEN` / `GITLAB_TOKEN_FILE` (no
CLI fallback in v1; `glab` exists but is rare, defer openly). Atlassian: ONE credential pair
serves Jira and Confluence: `ATLASSIAN_EMAIL` + `ATLASSIAN_API_TOKEN` /
`ATLASSIAN_API_TOKEN_FILE` (basic auth; that is how Atlassian Cloud tokens work). All through
the existing `tokens.resolve_token` seam. A configured Jira/Confluence with a missing
credential is the standard unavailable status with the standard how-to-fix message shape.

## 2. GitLab forge connector (collision + gate)

- **Collision:** `GET /api/v4/projects/{urlencoded slug}/merge_requests?state=opened&per_page=100`,
  changed files per MR via `GET .../merge_requests/{iid}/diffs?per_page=100` (paths from
  `new_path` + `old_path`). Normalization reuses `forge_review` verbatim (provider "gitlab"
  already exists in `ForgeProvider`): same truncation rule (full page anywhere -> stale
  status with the honest message), same own-branch rule (own = `source_branch == request
  branch` AND `source_project_id == target_project_id`; a fork MR never matches), same FYI.
  `source_display` reads "GitLab MR !12" (provider_name already dispatches).
- **Gate:** `GET /api/v4/projects/{slug}/pipelines?ref={branch}&per_page=1` for the LATEST
  pipeline of the ref, then its `status`: `success` -> clear; `running/pending/created/
  waiting_for_resource/preparing/scheduled` -> the existing `pending` state; `failed/canceled`
  -> firing gates from `GET .../pipelines/{id}/jobs?per_page=100` (failed jobs by name + web
  url; job-page truncation -> stale); `skipped/manual` and ANY unrecognized status -> fail
  closed to a firing "not confirmed green" treatment consistent with the GitHub non-passing
  rule (exact mapping is a build-time table with a test per status; unknown strings NEVER
  read green). No pipeline at all for the ref -> `disabled`-style honest note ("no pipeline
  ran for this branch"), never clear.
- **Render:** open hints use plain URLs (`web_url`); no `gh`-style CLI hint for GitLab in v1
  (the `_gh_hint` stays github-only by checking the provider through the card scope, which
  gains a `provider` field for forge cards).

## 3. Jira criteria connector

- **Issue refs are provider-shaped:** Jira keys look like `PROJ-123`. `discover.py`'s branch
  regex gains the Jira form `(?:^|[/_-])([A-Z][A-Z0-9]+-\d{1,6})(?=[/_-]|$)` and trailer
  parsing accepts bare keys after the closing keywords. Which tracker a ref belongs to is
  syntactic: `#N`/bare-N -> the forge's tracker; `KEY-N` -> Jira (when configured; a KEY-N
  ref with no Jira configured is a precise disabled note, never silently dropped).
- **Change detection:** per linked issue, `GET {base}/rest/api/3/issue/{key}?fields=summary,
  status,labels,updated` guarded by chronological `updated > since` (the S5a parser), then
  `GET .../issue/{key}/changelog?maxResults=100`: entries after `since` classify by
  `items[].field`: `description` -> body_edited, `status` -> state_changed, `labels` ->
  labels_changed (richer than GitHub events: field-level facts, no inference). Changelog
  pagination honesty: `isLast == false` after filtering -> the criteria source status goes
  stale with the honest "more history than checked" message.
- **Contract mapping:** same `criteria_changed` signals through `issue_criteria.normalize_issue_changes`
  with `source_display` "Jira PROJ-123: {summary}"; scope carries the browse URL
  (`{base}/browse/{key}`) for open-source.
- **Bounded-by-design:** the recon confirmed this Jira rejects unbounded JQL; we never issue
  JQL at all (per-issue GETs), which is the same bounded discipline the broker already has.

## 4. Confluence docs connector (docs family, remote)

- **Reliance declaration = the configured space.** Supersession marker, pinned:
  a Confluence CONTENT PROPERTY `teamctx.superseded_by` on the old page whose value is the
  replacement page URL or title (`GET /wiki/api/v2/pages?space-id=...` then per-page
  `GET /wiki/api/v2/pages/{id}/properties`; v2 recon-verified). Secondary signal: a page with
  status `archived` while still linked from a current page is NOT a v1 signal (defer openly;
  archived pages are excluded from the scan). A property-carrying page emits the same
  `doc_superseded` signal with `scope["doc"]` = the page title and `scope["superseded_by"]`
  = the property value; S5b's repo-wide match makes it fire without path coupling.
- **Coverage honesty:** space listing pagination (v2 cursor) exhausts up to a pinned budget
  (500 pages); hitting the budget -> stale status with the honest message. Unreachable /
  no-credential / malformed -> standard unavailable. A clean scan -> fresh (S5b's real green).
- **Local + Confluence together:** two coverage entries in the docs family; the closure's
  worst-status rule already composes them correctly (one stale -> the docs check cannot claim
  a complete green; verify with a test).

## 5. Onboard + status
`GitlabOnboarder` joins `ONBOARDERS` (host-aware detect; health = open-MR floor count,
mirroring GitHub's). Jira/Confluence cannot be detected from a working tree: onboard reports
them as configuration steps with exact how-to copy (final copy at build time, CTO-owned);
`status` shows their configured/reachable state through the same code paths (read-only twin
discipline). The reflex hook needs NO changes anywhere in Phase 4 (it rides the resolver).

## 6. Slices and builders
- **S9 GitLab forge** (collision+gate+onboarder+resolve generalization): the largest; codex
  builds from a plan; the resolve generalization gets its own plan task with a parity test
  matrix like onboard's.
- **S10 Jira criteria** (+ discover Jira-key support): codex or Opus.
- **S11 Confluence docs**: Opus.
- Each: TDD with synthetic payloads shaped like the recon captures; live read-only smoke by
  the CTO against the real instances before merge; adversarial review by the non-builder.

## 7. Validation bar (per connector, before "supported")
The connector's no-token, unreachable, malformed, truncated, and (where applicable) pending
paths each provably route to the correct non-fresh status and honest render line; a live
smoke against the real instance shows a true report; and the Phase 5 emulation exercises at
least one real cross-actor scenario through it.

## Open items for the spec review
- The GitLab pipeline-status mapping table (exact statuses -> clear/pending/firing/stale).
- Whether `scope["provider"]` on forge cards is the right dispatch for render hints.
- Confluence page-count budget value and whether per-page property GETs need batching.
- The disabled-note copy set for unconfigured Jira/Confluence (CTO writes at build).
