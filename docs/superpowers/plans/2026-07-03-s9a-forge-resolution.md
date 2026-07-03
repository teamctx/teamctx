# S9a: Forge-Resolution Generalization Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Repo identity becomes provider-aware end to end with zero behavior change for GitHub users: `detect_forge_repo` reads the origin host and returns (slug, forge); `parse_gitlab_repo` accepts gitlab.com URLs and multi-segment `group/sub/project` slugs; one `resolve_forge_repo` is shared by runtime AND onboard (the split-brain refusal extends to the forge field); `WorkStartInputs` gains `forge`; the config schema gains `forge`, `jira`, `confluence` blocks with the pinned validators.

**Architecture:** BINDING design: `docs/superpowers/specs/2026-07-03-source-breadth.md` revision 2, section 1 (forge resolution pins P1-8/P1-9, config validation pins P2-4, credentials pins P1-11) and section 5 (the onboarder Protocol + detection multiplexing pins P1-10). NOTE: `WorkStartInputs.profile` already exists (S8 introduced it); this slice adds `forge` beside it. GitLab CONNECTORS are NOT in this slice (S9b); this slice ends with: a gitlab-origin repo resolves and onboards correctly, and its collision/gate checks read an honest "GitLab isn't connected yet" disabled note, never a GitHub-bound query and never a clear.

**Branch:** worktree `git worktree add ../teamctx-s9a -b feat/forge-resolution main`. Gate per commit: the standard four + final coverage >= 90.

**Pinned copy (CTO-owned, verbatim):**
- disabled note when forge == gitlab (until S9b): `open MRs and pipeline state (this repo is on GitLab; the GitLab connector isn't wired yet, next slice)` for both git_hosting and ci_deploy family statuses, message: `This repo is on GitLab. The GitLab connector isn't wired yet; open MRs and pipeline state are not checked.`
- onboard detect failure copy generalizes: `could not determine a repo: not a git repo with a github.com or gitlab.com 'origin', no .teamctx/config.json, and no --repo. Re-run with --repo owner/name.`
- config forge mismatch is NOT an error (the forge field is authoritative; a mismatched origin fails honestly downstream per the spec).

### Task order (TDD per task, commit per task)
1. **`parse_gitlab_repo` + `detect_forge_repo`** (git_context.py): gitlab.com URL/scp/slug
   parsing with multi-segment paths preserved; `detect_forge_repo(root) -> (slug, forge) |
   None` by origin host; `detect_repo` stays as the github projection. Test matrix mirrors
   the existing parse_github_repo tests plus `group/sub/project`, and detection for both
   hosts + neither. Commit: `feat(git): provider-aware forge detection and gitlab repo parsing`
2. **Config schema** (project_config.py): `forge` on WorkStartConfig (default "github"),
   `JiraConfig`/`ConfluenceConfig` blocks with the base_url validators (trailing slash, the
   /wiki strip); `build_work_start_project_config` gains `forge`. Round-trip + validator
   tests. Commit: `feat(config): forge, jira, confluence blocks with normalizing validators`
3. **`resolve_forge_repo`** (resolve.py): the spec's precedence (config.forge >
   detected-forge; repo parsed UNDER the resolved forge); `resolve_github_repo` becomes the
   github case; `resolve_work_start_inputs` threads `forge` into `WorkStartInputs` (new
   field, `__post_init__` validates the slug under the forge). Tests: the parity matrix
   extended two-dimensionally (repo x forge sources). Commit:
   `feat(resolve): one provider-aware repo resolution for runtime and onboard`
4. **Runner honesty for the unwired forge**: when `inputs.forge == "gitlab"`, the runner
   emits the pinned disabled statuses for git_hosting + ci_deploy instead of calling the
   GitHub probes (issues/docs unaffected). Tests: a gitlab-forge input produces the honest
   notes, never a GitHub URL (capture opener asserts zero requests), never a clear conflict/
   gate. Commit: `feat(runner): gitlab-forge inputs read honestly-unwired, never GitHub-bound`
5. **Onboarder Protocol + multiplexed detection** (onboard.py): the `SourceOnboarder`
   Protocol; `GitlabOnboarder` with detect (host) + propose_config + auth_status
   (GITLAB_TOKEN env/file only, message copy mirrors GitHub's) + verify_health (open-MR
   floor via `GET /api/v4/projects/{quoted}/merge_requests?state=opened&per_page=100`,
   same floor semantics); detection multiplex: first claiming onboarder wins (github, then
   gitlab); the config write includes the winning forge. `run_status` mirrors. The
   onboard-vs-runtime parity tests run per forge. Commit:
   `feat(onboard): gitlab onboarder; detection multiplexed; parity holds per forge`
6. **tokens**: `resolve_atlassian_auth()` per the spec pin (pair or None, exactly-one-half
   -> None; no connector uses it yet, S10/S11 will; tested now so the seam is ready).
   CHANGELOG (Added): `- Repos hosted on GitLab now resolve, onboard, and report honestly ("the GitLab connector isn't wired yet"), laying the forge seam; config gains forge/jira/confluence blocks.`
   Commit: `feat(tokens): atlassian credential pair resolution; changelog`

## Completion
Stop after the last commit. Do NOT merge, push, or remove the worktree. Report: branch,
commits, gate tail, files changed, deviations. On plan-vs-code contradiction, stop and record.
