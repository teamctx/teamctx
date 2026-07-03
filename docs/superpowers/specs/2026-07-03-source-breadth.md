# Spec: source breadth: GitLab, Jira, Confluence (Phase 4)

## Status
Revision 2, after an Opus 4.8 adversarial spec review (verdict on rev 1: REVISE-FIRST; one P0,
eleven P1, five P2, all accepted by the CTO-arbiter and pinned below). **Hard prerequisites:
S5a (merged `b2a4773`) and S5b (in build) must be on main before any Phase 4 slice starts;
this spec leans on `parse_since`, the disabled-status machinery, provenance, and the
repo-wide docs match.** Grounded in live read-only API recon; no instance names or captured
payloads may enter fixtures.

## Goal
The four checks become source-plural: GitLab as a second forge (collision + gate), Jira as a
second issue tracker (criteria), Confluence as the first remote docs source (superseded
docs). Each connector proves the SAME honest-coverage behavior GitHub proved before it counts
as supported. **The one law, restated as the review invariant: no path from "no data" to a
clear. Every empty result must be distinguishable as verified-empty (fresh) vs
could-not-verify (non-fresh), and every reviewer-named hole below has a pinned closure and a
test.**

## Non-goals
No new card kinds. No cross-provider identity resolution. No webhooks/daemons. No writes.

## 1. Configuration, identity, credentials (pinned)

Config as rev 1 (`forge`, `jira`, `confluence` blocks) plus validation pins (review P2-4):
`jira.base_url` and `confluence.base_url` are normalized by validator (trailing slash
stripped; a trailing `/wiki` on confluence stripped, the connector appends it); Confluence
without Jira is VALID (docs only); the forge field is authoritative for parsing a bare slug.

**Forge resolution (P1-8, P1-9, pinned):**
- `git_context.detect_forge_repo(root) -> tuple[str, ForgeProvider] | None`: reads the origin
  host and returns BOTH the normalized slug and the forge (github.com -> github, gitlab.com
  -> gitlab, else None). `detect_repo` remains as the github projection for compatibility
  until callers migrate.
- `resolve.resolve_forge_repo(explicit, config_repo, config_forge, detected) -> (repo, forge)
  | error`: precedence for the forge is `config.forge > detected-forge`; the repo is parsed
  UNDER the resolved forge (`parse_github_repo` | new `parse_gitlab_repo`, which accepts
  gitlab.com URLs and multi-segment `group/sub/project` slugs). A config/origin mismatch
  resolves to config and fails honestly downstream (a 404 is an unavailable status, never a
  clear). `resolve_github_repo` becomes the github case. The onboard-vs-runtime parity test
  matrix EXTENDS to the forge field (same split-brain refusal, now two-dimensional).
- `WorkStartInputs` gains `forge: ForgeProvider = "github"`; `__post_init__` validates the
  slug under the forge (P1-8); `run_work_start_connectors` dispatches collision + gate probes
  on it. `RequestContext` needs no change (repo slug + provenance suffice; forge rides scope).

**Credentials (P1-11, pinned):** per-connector resolution AT THE RESOLVE LAYER, carried on
`WorkStartInputs` as distinct fields: `token` (forge token: GITHUB_TOKEN or GITLAB_TOKEN by
forge), `atlassian_auth: tuple[str, str] | None` (email, token) resolved by a new
`tokens.resolve_atlassian_auth()` reading `ATLASSIAN_EMAIL` + `ATLASSIAN_API_TOKEN`(_FILE).
EXACTLY one of the pair present -> None PLUS the connector-side unavailable message names the
missing half (fail closed, never partial). The hook resolves identically (it calls the same
resolver). CLI gains no new flags in v1 (env-only, like GitHub).

**Runner profile (P2-5, pinned):** `WorkStartInputs.profile: Literal["full", "reflex"] =
"full"`. The hook sets `reflex`; in reflex profile the Confluence connector is NOT run and
the runner emits its standard `disabled` docs status with the note: `Confluence docs are
skipped in the quick pre-edit check; run teamctx work-start for the full scan.` Every
surface stays honest about the skip; the hook's glanceable line is unaffected (docs is not an
important check).

## 2. GitLab forge connector (collision + gate)

**Collision:** as rev 1 (open MRs + per-MR diffs, per_page=100, truncation -> stale;
own = source_branch == request branch AND source_project_id == target_project_id). Corrections
from review P2-1/P2-2 (rev 1 claims were wrong): `normalize_forge_review_prs` gains
`provider` + `source_id` parameters (`"gitlab"` / `"gitlab_mr_metadata"`) and a terminology
dispatch: GitLab `source_display` = `GitLab MR !12` and `collision_summary` = `Open MR !12
changed ...` (surfaced-text principle; the PR/MR and #/! distinction is load-bearing).
Forge cards gain `scope["provider"]` (P1-7 pin): BOTH `_gh_hint` and `render_open_source`'s
collision branch gate on `provider == "github"`; GitLab findings show the `web_url` line
only. `finding_query`'s `pr:` selector matches gitlab collisions too (scope key stays
`pr_number` carrying the MR iid; the display distinguishes).

**Gate (P0-1, the law, pinned):** pipeline status mapping with the INVARIANT that any
non-`success` latest pipeline yields a non-clear outcome regardless of the jobs breakdown:
- `success` -> fresh (clear); zero-pipelines-for-ref -> `disabled` status with note
  `no pipeline ran for this branch, so the gate is unverified`, never clear.
- `running/pending/created/waiting_for_resource/preparing/scheduled` -> `pending`.
- `failed/canceled` -> failing gates from the jobs probe; **if the jobs list yields no named
  failing job (canceled-before-run), emit one synthetic FailingGate named `pipeline
  {status}` with the pipeline web_url** so the closure can never read complete-green.
- `skipped/manual`, any unrecognized status, or a malformed pipelines payload -> `stale`
  status with an honest "the pipeline state could not be confirmed green" message.
- A per-status test asserts the verdict is never `clear` for every non-success status.
- Deliberate asymmetry documented: GitHub's zero-check-runs continues to read clear (checks
  are per-commit attestations; absence of checks is absence of gates); GitLab's pipeline is a
  single stateful object whose non-green states are facts. Recorded here, not revisited.

## 3. Jira criteria connector (fail-closed pins P1-3, P1-4, P1-5, P1-6)

- **Ref dispatch (P1-6, pinned):** in `discover.py`, the Jira-key regex
  `(?:^|[/_-])([A-Z][A-Z0-9]+-\d{1,6})(?=[/_-]|$)` runs FIRST and its matched spans are
  REMOVED from the branch string before the numeric regex runs; trailers likewise accept
  `(?:fixes|closes|resolves)\s+([A-Z][A-Z0-9]+-\d{1,6})` with the same span-removal
  discipline. Tests: `PROJ-123`, `PROJ-123-fix`, `feat/ABC-7` derive ONLY the Jira ref.
- **Unconfigured-Jira KEY-N (P1-5, pinned):** a derived or explicit `KEY-N` with no
  `jira` config makes the runner emit a `disabled` `issue_tracker` status (source_id
  `jira_issues`) with note `issue {refs} looks like a Jira issue, but no Jira is configured;
  add work_start.jira to .teamctx/config.json`. The family then contains {fresh(github),
  disabled(jira)} -> `incomplete[stale-dep]` -> honest "couldn't check", NEVER a clear off
  the GitHub side alone. Test the mixed-family case explicitly, and add the S5a-interaction
  test: fresh+disabled must stay stale-dep (the all-disabled->policy-gap rule must not relax
  it).
- **Change detection fail-closed (P1-3, pinned):** missing or non-parseable `updated` on a
  Jira issue payload -> the Jira source status goes `stale` (never "unchanged"); a changelog
  GET failure on a known-changed issue still emits the criteria-changed signal with generic
  detail (matches GitHub's behavior, now stated and tested for Jira); absent/malformed
  `isLast` is treated as NOT last -> `stale`. All comparisons through S5a's `parse_since` on
  both sides (hard prerequisite).
- **Normalize gains channels (P1-4, pinned):** `normalize_issue_changes` gains
  `source_id: str` and `coverage_truncated: bool` parameters and `IssueCriteriaChange` gains
  `source_display: str` (built by each connector: GitHub `GitHub Issue #5: {title}`, Jira
  `Jira PROJ-123: {summary}`), so truncation reaches `stale` and the two trackers are two
  distinct family entries (`github_issues`, `jira_issues`).
- Scope carries the browse URL for open-source; `finding_query`'s `issue:` selector matches
  Jira keys case-insensitively without requiring `#`.

## 4. Confluence docs connector (coverage pins P1-1, P1-2, P2-3)

- **Identity thread (P1-1, pinned):** the connector sets `SupersededDoc.repo =
  request_context.repo` so signals carry `scope["repo"] == request.repo` and the derive's
  repo gate passes. A broker-level test proves a superseded Confluence page fires a card.
- **Space resolution (P1-2, pinned):** `space_key` -> space id via
  `GET /wiki/api/v2/spaces?keys={key}`; zero accessible spaces -> `unavailable` ("the
  configured Confluence space couldn't be found with current access"), never an empty clean
  scan. Malformed/absent pagination cursor or a malformed page payload -> `stale`/
  `unavailable`, never assume-last-page. Per-page property fetch: prefer the key-filtered
  form (`.../properties?key=teamctx.superseded_by`); ANY per-page property failure -> the
  docs source goes `stale` (skip-and-continue is banned). Budget 500 pages in full profile;
  budget-hit -> `stale` with the honest message. Reflex profile: not run (section 1).
- **Openability (P2-3, pinned):** `SupersededDoc` gains `url: str | None`; Confluence fills
  the page webui link; `render_open_source`'s doc branch prints the URL when present, the
  path otherwise. Distinct source_id `confluence_pages` vs local `docs_supersession`; the
  two docs sources are two family entries and the closure's worst-status rule composes them
  (tested: local fresh + confluence stale -> docs cannot read complete-green).

## 5. Onboard + status (P1-10, pinned mechanics)

`ONBOARDERS` becomes a typed Protocol list (`SourceOnboarder`: `provider`, `detect(root)`,
`propose_config`, `auth_status`, `verify_health`). Detection multiplexes: each onboarder's
`detect` sees the origin URL; the FIRST claiming onboarder wins (github, then gitlab); its
provider writes `work_start.forge` via `build_work_start_project_config(repo=..., forge=...)`
(the function gains the parameter). GitLab health = open-MR floor count. Auth copy is
per-provider. Jira/Confluence are reported as config steps with exact how-to copy (CTO writes
at build); `status` mirrors everything read-only through the same helpers. The
onboard-vs-runtime parity matrix runs per forge.

## 6. Slices and builders (re-cut after review)
- **S9a forge-resolution generalization** (detect_forge_repo, parse_gitlab_repo,
  resolve_forge_repo, WorkStartInputs.forge + profile field, parity matrix): its own slice,
  BEFORE the GitLab connector; codex builds.
- **S9b GitLab collision + gate connector** (+ forge_review parameterization, provider-gated
  render hints, onboarder + registry protocol): codex builds; live smoke against the real
  GitLab account before merge.
- **S10 Jira criteria** (+ discover Jira-key dispatch, normalize channels, disabled
  unconfigured-Jira emission): Opus builds.
- **S11 Confluence docs** (+ SupersededDoc url, space resolution, profile skip): Opus builds.
- Every slice: synthetic payloads shaped like the recon captures; the non-builder reviews;
  CTO live-smokes read-only before merge.

## 7. Validation bar (per connector, unchanged)
No-token, unreachable, malformed, truncated, pending (where applicable), and EVERY
reviewer-named hole above provably route to the correct non-fresh status and honest render
line; live read-only smoke shows a true report; Phase 5 exercises at least one real
cross-actor scenario through it.
