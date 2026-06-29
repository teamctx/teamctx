# Spec: onboard and the runtime-honesty pass (2026-06-29)

## Status
Proposed, revision 3 (after codex round 5). Hardened through a five-round adversarial reviewer
loop (codex gpt-5.5, xhigh), with the architect as CTO-arbiter verifying each finding against
the code. Round 5 returned no P0 and confirmed the section 1.7 carrier is viable and correctly
targeted; revision 3 closes its remaining items: the identity invariant is enforced at every
boundary (1.2), the two new honesty states have pinned assessment-kind and render buckets (1.6),
the docs scanned-path data flow is named (1.5), and the root-helper default-argument footgun is
fixed (1.1). Pending Edgar's approval. No code until approved.

## Goal
Make teamctx usable with zero flags and zero false confidence. Today real use needs too much
setup (pip install, `teamctx init`, export a token, `install-hook`, paste a CLAUDE.md snippet)
and too many per-run flags. The visible payoff is a single `onboard` command. The
non-negotiable underneath it: the setup command must report exactly what the runtime will
actually do. A setup command that detects one truth while the hook, CLI, and MCP resolve
another is a false confidence machine, which is the one failure this product exists to refuse.

## Root cause this slice closes (from the reviewer loop)
Setup/runtime split-brain. The runtime resolution layer (repo root, repo identity, credential)
is inconsistent across surfaces and overclaims in its copy:
- repo identity is host-blind: `detect_repo` / `parse_owner_name` return owner/name from any
  remote (git_context.py:33), connectors hardcode api.github.com (github.py:20).
- the token resolver is env/file only (tokens.py:10); hook/CLI/MCP all call it, so a `gh`
  login is never consulted at runtime.
- root resolution is cwd-based at runtime (cli.py:201, mcp_server.py:73) while the hook uses
  git toplevel (hook.py:101).
- the gate says "CI is green" and "required" without proof; docs renders "current" even when
  no relied-on doc was checked. Crucially, the deterministic core has no way to even represent
  "checks still running" or "no relied-on doc in scope" (section 1.7), so today both collapse
  into a false clear or a false "couldn't reach."

## Principle
One shared, honest resolution layer (root, identity, credential) used identically by hook, CLI
work-start, MCP, and onboard. Every check surfaces its real status exactly once; a clear means
checked, never guessed; where we could not look we say so. onboard reports through the same
resolvers the runtime uses, so its report cannot drift from runtime behavior.

## Scope
In: the runtime-honesty pass (Part 1) and the onboard command on top of it (Part 2). Bundled by
decision (Edgar, 2026-06-29): onboard's honesty depends on Part 1, so they ship together.

Note on the core contracts: section 1.7 adds two values to `SourceStatusValue` and two to
`Completeness` (additive extensions to the v0 contracts). There is no honest alternative: the
core is what composes coverage and completeness, so a new coverage state has to live there, not
in a layer that bypasses the core. The protocol-version implication (additive within v0, or a
documented v0 bump) is called out in 1.7 for Edgar's approval.

Deferred, on merit (separable capabilities, built fully when they land, not scope-cut):
- GitHub Enterprise / custom API host (needs the API host threaded through all three
  connectors; fail closed until then).
- A provider/host field in the persisted config schema (arrives with the second provider's
  connector; see the identity decision in 1.2).
- Real gate requiredness semantics (cross-referencing branch-protection required checks); this
  slice stops claiming "required," it does not yet prove it.
- Docs as a firing check (needs doc-reliance discovery and the path-gating fix); this slice
  stops the false "current," it does not yet make docs fire.
- onboard `--with-mcp` and `--global`.
- Linked-issue and `since` auto-discovery (the next slice).

## Part 1: shared, honest runtime resolution

### 1.1 One shared repo-root helper
New `git_context.resolve_project_root(start: Path | None = None, override: Path | None = None)
-> Path`. `start` defaults to `None` and is resolved to `Path.cwd()` inside the function, not as
an import-time default argument (that footgun is why the signature is not `start: Path =
Path.cwd()`). Precedence: `override` if given, else the git toplevel of `start`
(`git rev-parse --show-toplevel`), else `start` (cwd fallback, so non-git trees still work).
Generalizes the hook's `_git_toplevel` (hook.py:101).

Call sites that must route through it:
- CLI work-start (cli.py:201, 206, 277, 281) and `init` (cli.py:82): start = cwd.
- The hook (hook.py:47): start = the event cwd, so its resolution root becomes git-toplevel
  anchored, consistent with everyone else.
- MCP (mcp_server.py:73): override = `TEAMCTX_PROJECT_ROOT` if set (mcp_server.py:71),
  preserving the existing override; else start = cwd. Keeps test_mcp_server.py:125 and non-git
  config use working.
- Authority loading (work_start.py:18, 35) and the dev `_work_start_view` (cli.py:661): anchor
  `.teamctx/authority.json` to the resolved root.
- `install-hook` (cli.py:562, 593): write `.claude/settings.json` under the resolved root.
- The dev `docs-probe` passes `base_dir` to the docs connector (cli.py:428, docs.py:46): anchor
  it to the resolved root, not `Path(".")`.

Effect: every surface agrees where the project is. Non-git degrades to cwd, never to a guess.

### 1.2 Repo identity, host-validated end to end (Option A, approved)
Decision: keep the persisted config flat (`work_start.repo` stays `owner/name`), defined and
validated as a github.com repo at every entry, with git detection host-aware and fail-closed.
The persisted schema gains a provider field only when a second provider's connector lands.

The invariant: no path can let a non-github.com repo reach the GitHub connectors.
- `detect_repo` (git_context.py:33) becomes host-aware: it returns `owner/name` only when the
  origin URL host is github.com (ssh `git@github.com:`, https `github.com/`); any other host
  returns None. A new `parse_github_repo(value) -> owner/name | None` validates the slug shape
  and (for URLs) the host.
- `resolve_work_start_inputs` (resolve.py:51) validates the resolved repo from every source
  (explicit `--github-repo`, config, git-detect) through `parse_github_repo`. A non-github
  origin with no explicit/config repo yields the existing honest error (`_REPO_UNRESOLVED`,
  resolve.py:23), not a silent GitHub query.
- `init` validates its `--repo` through `parse_github_repo` before writing config (cli.py:82-91),
  so an invalid or non-github repo never reaches `.teamctx/config.json` in the first place.
- The dev probes that take a raw `--repo` and call connectors directly, bypassing
  `resolve_work_start_inputs` (cli.py:116, 434, 474), validate their `--repo` through the same
  helper. No carve-out.
- `WorkStartInputs` validates `repo` through `parse_github_repo` on construction (a frozen
  dataclass `__post_init__`), raising on an invalid value. This is the single chokepoint before
  the runner (runner.py:23-40, 69), so `resolve_work_start_inputs`, the dev probes that build
  inputs, and any direct Python construction are all covered. The invariant is enforced, not just
  documented. The runner then runs the GitHub connectors, correct by construction.
  Provider-variant gating in the runner arrives with the second provider.

Why Option A and not a provider field now: GitHub is the only provider with a connector, so
`repo: owner/name` meaning "a GitHub repo" is a true and complete statement, and the honesty
requirement is met fully by validating it and failing closed on non-GitHub origins. Writing a
provider into the persisted schema before its connector exists is the speculative-schema trap
the reviewer flagged in round 1.

### 1.3 GitHub token resolver with gh fallback, at runtime
New `resolve_github_token(token_env: str = "GITHUB_TOKEN") -> str | None`: `token_env` value,
then `{token_env}_FILE`, then, only when `token_env` is the default `GITHUB_TOKEN`,
`gh auth token` (subprocess, short timeout, errors to None, import-light, no broker import).
- Exact semantics (closes the round-4 ambiguity): the `gh` fallback fires only on the default
  `GITHUB_TOKEN` path. A custom `--token-env` means the user has taken explicit control of the
  credential source, so it is env-plus-file only, with no `gh` fallback. This preserves the
  existing "force the no-token path with a custom unset env var" behavior (test_work_start_cli
  .py:30) exactly.
- Route the GitHub runtime call sites through it: hook (hook.py:139), MCP (mcp_server.py:63),
  CLI GitHub work-start sites (cli.py:200, 276, 467, 510, 653).
- Generic `resolve_token(token_env)` (tokens.py:10) is unchanged (env/file), so a future
  non-GitHub source never receives a GitHub credential. test_tokens.py contract preserved.
- Test determinism: the `gh` step is also skipped when `TEAMCTX_DISABLE_GH_AUTH` is set; the
  suite sets it globally (conftest) as belt-and-suspenders for tests that use the default env.
  Targeted tests of the `gh` fallback mock the subprocess.

### 1.4 Gate honesty
Stop claiming "required." Sweep the word out of user-facing copy: the gate evidence string
(gate_status.py:66), the card render (select.py:86, 273), the README (README.md:24), and the
MCP tool description (mcp_server.py:27). The clear copy "CI is green" (contract_render.py:27,
hook_signal.py:17) becomes "no failing checks found." We report failing checks honestly; we do
not assert they are required (deferred).

Surface pending checks. Today in-progress runs (conclusion None) are silently skipped
(github_checks.py:117, 119), so a branch whose checks are still running reads as green. New
behavior: when the probe sees runs that are not completed (status queued / in_progress) and
none failing, the gate cannot assert all-clear, so it emits a `pending` source status carried
through the core (1.7) to a "checks still running" render. A visible failing run still
falsifies the gate (a found finding). Precedence within the gate, when both occur (a failing
run and other runs still pending): `found` wins. A concrete failing check is the actionable
signal; pending is surfaced as the gate status only when there is no failing run. Nothing
actionable is hidden, so this needs no multi-state model.

### 1.5 Docs honesty
- `init` stops auto-enabling `docs_root`: drop the auto-detect default at cli.py:89 so init no
  longer defaults `docs_root` to `_detect_docs_root(root)`; an explicit `--docs-root` is still
  honored. onboard does not write `docs_root` either.
- New honesty state via the carrier (1.7): the docs connector has `request_context.paths`. When
  `docs_root` is scanned but no scanned doc is in `request.paths` (nothing relied-on in scope),
  it emits a `not_applicable` source status (instead of the current hard-coded `fresh` at
  docs_supersession.py:81), carried to a docs `not_applicable` render that is neither "current"
  (a clear) nor "not configured." This closes the false green for old configs and explicit
  `--docs-root`. Data flow to fix: `run_docs_supersession_probe` (docs.py:39-61) currently keeps
  only the superseded docs from `parse_superseded_docs` and discards the scanned paths, so
  `normalize_superseded_docs` (docs_supersession.py:43) cannot tell "a relied-on doc was scanned
  and is current" from "no scanned doc was in request.paths." The probe must compute the in-scope
  check (any scanned rel-path in `request_context.paths`) and pass it into
  `normalize_superseded_docs` (a signature change), which then emits `fresh` versus
  `not_applicable` accordingly.
- Docs becomes a firing check in the auto-discovery slice. Until then no surface says docs are
  current unless a relied-on doc was actually evaluated and found current.

### 1.6 Assessment model: two new first-class states, pinned end to end
`assessment.py` `CheckStatus` (assessment.py:18) gains `pending` and `not_applicable`.
`_status_for` (assessment.py:48) maps the 1.7 completeness reasons: `incomplete[pending]` to
`pending`, `not_applicable[out-of-scope]` to `not_applicable`. Neither is a clear and neither is
a finding.

Kind precedence (assessment.py:82-88), pinned: any `found` gives `heads_up`; else any IMPORTANT
check (conflict, gate) that is `pending` or `unreachable` gives `cant_verify`; else `ready`.
Only the gate can be `pending`, and because a failing run is `found` and `found` dominates (the
found-over-pending rule in 1.4), pending reaches the kind logic only when there is no failure.
`not_applicable` is a non-important docs state, so like today's `not_configured` it never changes
the kind and never blocks `ready`.

Render buckets (contract_render.py:82-164), pinned so every status is surfaced exactly once:
- `cant_verify` is generalized from "couldn't check the important things" to "I can't confirm the
  important things yet," with per-check bullet reasons: `unreachable` gives "couldn't reach
  GitHub" (existing), `pending` gives "checks still running, not confirmed green yet."
- `not_applicable` (docs) gets its own coverage line, distinct from the `Couldn't check`
  (unreachable) and `Not checked` (not_configured) lines: a `Not applicable` line, for example
  "Not applicable: docs (a docs root is set, but none of the files in scope are docs you rely
  on)."
- `clear`, `found`, `unreachable`, and `not_configured` keep their existing buckets.

Hook (hook_signal.py:23-31), pinned: the single `_cant_verify` branch (hook_signal.py:29) splits
to distinguish a `pending` gate ("CI checks are still running, so the gate is not confirmed green
yet") from an unreachable source (existing copy). `not_applicable` docs stays unheadlined in the
hook, exactly as `not_configured` is today, because the hook deliberately suppresses low-stakes
coverage gaps; the full CLI render is where `not_applicable` is surfaced.

### 1.7 The core-contract carrier (the round-4 P0)
The two states above cannot be bolted on at the assessment layer, because assessment is
downstream of the deterministic core, and the core currently has no representation for them:
`SourceStatusValue` is `fresh/stale/unavailable/blocked/disabled` (contracts.py:52), and
`assess_completeness` (select.py:408) collapses every non-fresh status to
`incomplete[stale-dep]` (select.py:426), which `_status_for` renders as "couldn't reach
GitHub." The docs connector hard-codes `status="fresh"` (docs_supersession.py:81). So pending
would read as unreachable and out-of-scope docs as current unless the core carries the states.

The carrier, end to end:
1. Connector source status. `SourceStatusValue` (contracts.py:52) gains `pending` and
   `not_applicable`. The gate connector (github_checks.py) emits `pending` when there are
   incomplete runs and none failing. The docs connector (docs_supersession.py:76) emits
   `not_applicable` when `docs_root` was scanned but no scanned doc is in `request.paths`.
2. Completeness. `Completeness` (select.py:377) gains `incomplete[pending]` and
   `not_applicable[out-of-scope]`. `assess_completeness` (select.py:408) is refined to classify
   a dependency family by its worst status, with precedence: any
   stale/unavailable/blocked/disabled gives `incomplete[stale-dep]` (a real unreachable
   dominates), else any `pending` gives `incomplete[pending]`, else a family whose only
   non-fresh status is `not_applicable` gives `not_applicable[out-of-scope]`, else `complete`.
3. Valuation. The affected proposition (`all_gates_pass`, `no_superseded_docs`) carries the new
   completeness reason as its valuation reason, with value `unknown` (we did not establish the
   universal; we are honest about why).
4. Assessment and render. `_status_for` maps `incomplete[pending]` to `pending` and
   `not_applicable[out-of-scope]` to `not_applicable`; the renders speak the honest lines.

Protocol note for approval: these are additive enum extensions to the v0 contracts. They do not
remove or change existing values, so existing documents stay valid, but they do widen the
published vocabulary. Decision needed at approval: treat as additive-within-v0 (with a changelog
note) or stamp a documented v0 revision. Recommendation: additive-within-v0 with a changelog
note, since nothing existing changes shape.

## Part 2: onboard

### 2.1 The minimal source-onboarder seam
A plain registry (a list) with one entry today (github), built over Part 1. Each onboarder
exposes `detect(root) -> identity | None` (host-aware origin from 1.2), `propose_config() ->
fragment` (`{repo: owner/name}`), `auth_status() -> credential state + how-to-fix` (via
`resolve_github_token` from 1.3, the same resolver the runtime uses), and `verify_health() -> a
live reachability report` (never a verdict). No ABC, no future stubs.

### 2.2 The onboard flow
1. Resolve the shared root (1.1). If not a git repo and no `--repo`, honest error with the fix.
2. Run detect (1.2). If no supported source applies, say so honestly and stop, writing nothing.
3. Write `.teamctx/config.json` atomically (temp file, then rename) anchored to the root.
   `--force` to overwrite, never a silent clobber.
4. Ensure config is trackable (2.3).
5. Report the credential path via `resolve_github_token` (1.3): "using your gh login" / "using
   GITHUB_TOKEN" / "using GITHUB_TOKEN_FILE" / "not found, here is the one thing to do." Never
   store the token.
6. Install the hook (reuse install-hook, anchored to the root via 1.1).
7. Write the CLAUDE.md snippet (2.4).
8. Run `verify_health` with a count-honest open-PR fetch (2.5).
9. Print one "what changed" summary (per step: wrote / already present / skipped / failed with
   reason) plus the single next step.

Flags: `--repo`, `--force`, `--yes` (non-interactive), `--dry-run` (preview, write nothing).
Deferred: `--with-mcp`, `--global`, docs auto-enable.

Transaction model: steps are additive and idempotent; each file write is atomic (temp +
rename); no cross-step rollback. A malformed existing `.claude/settings.json` fails only its own
step with a how-to-fix; other steps still run. A missing token does not abort: config and hook
are still written and the gap is reported as the remaining to-do.

### 2.3 Making config trackable (the gitignore fix)
A nested `.teamctx/.gitignore` cannot un-ignore a directory a parent already ignores. So:
- In teamctx's own repo, change `.gitignore:26` from `.teamctx/` to `.teamctx/*` then
  `!.teamctx/config.json`. This also lets the dogfood fixture commit a shared config.
- onboard writes or patches the user repo's root `.gitignore` to the same pattern.
- Verify with correct exit semantics: `git check-ignore` returns exit 1 when a path is not
  ignored. Use `git check-ignore --no-index` (or `git status --short`) to confirm
  `.teamctx/config.json` is trackable without a tracked-file false pass.

### 2.4 The snippet, honest and migration-safe
- Fix the shared constant `_CLAUDE_MD_SNIPPET` (cli.py:543) to claim only what auto-fires
  today: open PRs touching your files, and failing checks. Remove "changed specs" and
  "superseded docs." This honest text is what both `install-hook` (cli.py:589, 596) and onboard
  print/write.
- Wrap the written block in paired markers (`<!-- teamctx:start -->` ... `<!-- teamctx:end -->`)
  and update in place between the markers (idempotent, exact, no boundary guessing).
- Migration of an old unmarked block, with a safe boundary (closes the round-4 "could delete
  user edits" risk): match only a confident exact or whitespace-normalized match of the known
  old snippet constant, and replace exactly that span. If the `## Team context (teamctx)`
  heading is present but the body does not confidently match our known old snippet (the user
  edited it), do not auto-replace: leave it untouched and print a warning telling the user to
  remove the old block manually. Never replace by a guessed section boundary, so user content
  adjacent to the old block is never deleted.

### 2.5 Count-honest verify_health
`verify_health` must not reuse the work-start PR probe's `truncated` boolean, which conflates
PR-list truncation and per-PR file-list truncation (github.py:39, set at both github.py:111 and
github.py:127). It does its own lightweight open-PR count fetch: read the first page of open
PRs; if the page is full (>= 100), report "at least 100 open PRs" or "100+"; otherwise the exact
count. So the health line is honest about whether the count is a floor.

## Test impact
Changed: test_init_command.py:83 (no docs auto-enable); test_mcp_server.py:125 (root override
preserved); test_work_start_cli.py:30/124 (deterministic under the gh fallback) and
test_work_start_cli.py:84 (the "CI is green" / docs "current" copy changes);
test_render_broker_answer.py:131 ("Also checked: CI is green" copy); test_install_hook.py
(honest snippet + root anchoring); test_gate_status.py:51 (in-progress now surfaces pending).
New: host-aware detect_repo and `parse_github_repo` (a gitlab origin yields None); resolve and
dev-probe identity validation; resolve_github_token gh fallback (mocked), its default-only rule,
and the custom-token-env no-gh rule; the 1.7 carrier (SourceStatusValue + Completeness
additions, assess_completeness precedence, valuation reasons) for both pending and
not_applicable; gate pending render and the found-over-pending precedence; docs not_applicable
render; verify_health count-honesty (floor vs exact); the gitignore negation (git check-ignore);
snippet migration (exact-match replace, and warn-not-delete on an edited old block); `init
--repo` validation and `WorkStartInputs` construction-time validation (an invalid repo is
rejected at every boundary); the pinned kind precedence and render buckets (cant_verify
generalized to cover pending, the `Not applicable` line, the hook pending branch), each surfaced
exactly once; the docs scanned-path-to-status data flow through `docs.py` into
`normalize_superseded_docs`; and the `resolve_project_root` no-import-time-default signature.

## Sequencing
Within the slice: Part 1 (1.1 to 1.7) is the floor and lands first or together; onboard
(Part 2) sits on it. The keystone is 1.1 to 1.3 (root, identity, credential), which kill the
split-brain; 1.4 to 1.7 are the honesty states and their core carrier; Part 2 is the visible
command.
Next slice: auto-discovery (linked issue and `since` from the branch/PR, the docs path-gating
fix, and expanding the snippet to claim all four checks). Then GitLab and Jira plug the
detect/registry seam.
