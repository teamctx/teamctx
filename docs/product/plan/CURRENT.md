# CURRENT: teamctx rolling plan

**The one current plan. Read this first every session and re-orient before acting.**

## Product framing (decided 2026-06-27)

teamctx is **fundamentally a deterministic, honest broker over the team's scattered
sources of truth.** Its value is the composed *verdict* + honest-UNKNOWN coverage, NOT the
integrations themselves (that's the aggregator trap). **Work-start is the canonical, primary
consumption surface** (the moment a unit of work begins), not a ceiling. Direction is
**(A) broker with widening coverage**: more sources enter as pluggable connectors → one
common contract → pure deterministic core → render, and explicitly **not (B)** a unified
team-context substrate. Breadth is fuel for the one operation, never the product itself.

**North star (decided 2026-06-27):** teamctx is *reality-grounding for agentic work*: **no LLM
in the content path**: it transforms *delivery, not content*, and is faithful to the
source-of-record (*fidelity ≠ truth*, not universal truth). Lay the floor early. Lead positioning
against the **context-engine** category (Unblocked), NOT agent-memory. Full strategy:
[reality-grounding](../vision/reality-grounding-strategy-2026-06.md) ·
[competitor analysis](../../research/competitive-context-engines-2026-06.md).

## Operating model (synced 2026-06-27)

- **Build each capability complete to the bar.** *Sequencing* (a separable thing built
  fully, later) is fine; **cutting scope to save effort is not.** Defer openly, never silently.
- **Decide/recommend on merit**: correctness, the honest-UNKNOWN promise, user mental model,
  genuine risk class. Never on "smaller / finishable / least-code / land-green."
- Guidelines (CLAUDE.md, memory, Field Manual) are guidelines: bend them when it makes a
  better product, within reason, best shippable product, not perfection regardless of time
  ("we can't take months").
- **CTO/CPO:** CTO makes the judgment calls and checks the CPO on genuine product or
  hard-to-reverse decisions. Plan a few sprints ahead; update when state meaningfully changes
  (not a rigid per-slice ritual).

## Where we are (NOW: 2026-06-27)

Engine complete (4 card kinds; T1/T2/T5/S2 in code). All four certified kinds have live
**GitHub** connectors. MCP transport shipped **and dogfooded** (a real agent consumed
`work_start` over MCP and reasoned correctly about honest-UNKNOWN). Foundation hardened (one
model, `core/broker.py` entry point, unified `work-start` runner). 212 tests; ruff + mypy
strict + CI green. teamctx.dev landing page on Vercel (pending DNS `A` record). The
`refresh`/`context` snapshot flow is **legacy**: frozen since 2026-06-16 while the product
moved to the live broker; retired in Sprint 2.

## 2026-07-04: THE NEXT ARC IS AMBIENT (read the plan first)

The CPO set the product frame 2026-07-04: users NEVER run commands; team context is ambient
and appears like magic, or nobody will use it. The committed plan translating that frame into
workstreams (moments, actors, feel, copy, evidence) is
**`docs/product/plan/2026-07-04-ambient-magic-plan.md`**: read it FIRST next session; it
supersedes "what's next" below. Reviewed adversarially (rev 2 pins all 12 findings; the committed-hook idea is formally rejected) and **APPROVED BY EDGAR 2026-07-04 ('approved, keep going')**. B1 DONE (merged: the reflex installs to settings.local.json, migration surgical and behaviorally verified). A-1 DONE (branch-scoped gate; empty paths never clear). A-2a DONE (merged: continuous grounding under the silence law; content digest + per-session baselines; the marker is gone; 863+ tests). A-2b DONE (merged: the delta voice, 900+ tests; the arbiter's live smoke caught a class-taxonomy hole that would have re-spoken on every edit in branchless repos, fixed + spec corrected). WORKSTREAM A COMPLETE: onboard once, context appears, reappears exactly when reality changes, silence is lawful. C+E DONE (merged: zero-network silence and request budgets pinned in the suite; the four delta rows land the matrix at 16 of 16). Claims refreshed on every surface, precision-reviewed. **THE AMBIENT ARC IS COMPLETE: built, proven, and described exactly.**

**PYPI FLIPPED 2026-07-07 (Edgar's call): `pip install teamctx` is LIVE**
(https://pypi.org/project/teamctx/0.1.0/, verified by a fresh-venv install from PyPI +
onboard smoke). Still parked, Edgar's separate switches: repo public, site deploy, DNS.
Token hygiene owed: replace the account-wide PyPI token with one scoped to teamctx.
The five-minute user guide (docs/user-guide.md, claims-reviewed) is ready to hand out;
issue #7 tracks the first-prompt install gap for 0.1.1.

**Prior staging record (2026-07-04):** The landing page wears
the engineering-record design (print-inspired, zero JS, verbatim samples; merged). The 0.1.0
release sits COMPLETE and adversarially reviewed on branch `release/0.1.0` (pushed): version
+ Alpha classifier, artifact audited to zero name/instance/credential hits, shipped suite
passes with and without the mcp extra in a fresh venv, twine check green, the one hatchling
.gitignore exception verified and documented. THE FLIP, when Edgar says go: (1) he creates a
PyPI API token -> `.secrets/pypi-token`; (2) merge `release/0.1.0` to main; (3) `git tag
v0.1.0 && git push origin v0.1.0`; (4) `python -m build && TWINE_USERNAME=__token__
TWINE_PASSWORD=$(cat ~/.secrets/pypi-token) twine upload dist/*`; (5) verify `pip install
teamctx` from PyPI; separate switches, also his: repo public, site deploy (Vercel), DNS.
Publishing the package publishes the source (an sdist is the code). Superseded sequencing: Workstream C then E (the delta evidence rows). The delta-engine spec (`docs/superpowers/specs/2026-07-04-ambient-delta-engine.md`, in review).
The ambient copy law is also in auto-memory (feedback_teamctx_ambient_never_commands).
Landing page + README + validation evidence all shipped 2026-07-04 (see below); main clean
at `93f450b`+.

## 2026-07-03: full review + delegated build-out (the active arc, COMPLETED)

A full code/product/architecture review of main `54ca04e` landed 13 findings (no new
false-clear paths; the honesty invariants held). Findings + locked designs:
`docs/superpowers/specs/2026-07-03-full-review-findings.md`. Edgar approved incorporating
all of it and delegating the build: **Fable is CTO/head-eng; building is offloaded per
slice to the strongest available model.** This section supersedes the "Next slice" ordering
below until the arc completes.

**Operating model for the delegated build:**
- **CTO (Fable):** architecture, specs, all surfaced-text copy (voice rules are strict),
  final review of every diff, merges, plan upkeep.
- **Builders:** codex (gpt-5.5 xhigh, local CLI) for tightly-specced slices; Opus 4.8
  subagents for multi-file refactors and parallel test work; Fable for copy-heavy and
  core-semantics slices.
- **Reviewer separation (Field Manual):** whoever built a slice never reviews it. codex
  adversarially reviews Fable-built diffs; Fable arbiter-reviews codex/Opus-built diffs;
  optional second-opinion review via OpenRouter models on core-invariant merges (S6, S8,
  Phase 3 methodology).
- **Gate per slice (unchanged):** feature branch, TDD, `pytest -q` + `ruff check src tests`
  + `mypy --strict src` + em-dash grep, adversarial review before merge, merge --no-ff +
  push when green.

**Phases (each slice complete to the bar; sequencing is not scope-cutting):**
- **Phase 0, review hardening (before the multi-actor dogfood):**
  S1 own-PR collision fix **DONE 2026-07-03 (merged `6cada7b`, 443 tests; codex built from the
  plan, Fable arbiter-reviewed + one copy fix; own-branch PRs set aside with an FYI line and
  recorded on the forge source status)** ·
  S2 README refresh + docs-claim tightening + gh-hint repo flag (F3, F11) **DONE 2026-07-03
  (merged `469cf65`; Fable built, codex adversarial review returned FIX-FIRST with three real
  overclaims in the copy (identical-facts, "verbatim", own-PR scope), all fixed before merge;
  samples byte-verified by the reviewer against the render)** · S3 `status` made
  real as onboard's read-only twin (F2) **DONE 2026-07-03 (merged `ea0cbef`, 455 tests; codex
  built in an isolated worktree from the plan, Fable arbiter-reviewed + live smoke: every
  status line true, real reachability call)** · S4 small batch:
  authority.json fail-closed, CI 3.12+3.13 matrix + coverage gate wired (93.12% > 90),
  teamctx-mcp friendly import guard (F6, F8, F10) **DONE 2026-07-03 (merged `950f0a3`, 464
  tests; codex built from the plan, Fable arbiter-reviewed)**. **PHASE 0 COMPLETE.**

**Execution re-sequencing (CTO, 2026-07-03, merit-based):** S6+S7 (structural) land BEFORE
Phase 1, because S5b must extend the exact registries S6 consolidates (building S5 first
means immediate rework), and the Phase 3 proof numbers move AFTER Phase 5, because the
emulation's scripted scenarios ARE the labelled conformance corpus Phase 3 needs. Order:
Phase 0 → S6+S7 → S5a/b/c → S8 → Phase 4 breadth → Phase 5 emulation → Phase 3 numbers.
Design spec for S6/S7/S5 (locked designs, pending codex adversarial spec review before
build): `docs/superpowers/specs/2026-07-03-autodiscovery-and-structure.md`.
- **Phase 1, auto-discovery (was "next slice"; absorbs F9, F13):** S5a linked-issue +
  `since` derivation **DONE 2026-07-03 (merged `b2a4773`, 502 tests, coverage 93.37%; codex
  built from the plan, Fable arbiter-reviewed + live smoke showing the precise not-run notes;
  discover.py from branch names + local trailers only, privacy boundary intact, provenance
  bound into the replay digest)** · S5b docs relied-on semantics **DONE (merged `0ad1286`,
  505 tests; Opus built, Fable reviewed; clean scan is a real green)** · S5c onboard docs
  detection + truthful snippet + README **DONE (merged `65b6a81`, 517 tests, coverage
  93.58%; Fable built, codex adversarial loop took FOUR rounds, each catching a real copy
  lie in the docs-step state matrix (existing-config path, empty dir, symlink-unsafe root,
  malformed-config promise); the matrix (config present/missing/malformed x docs dir
  ok/unsafe/empty/absent) is now enumerated with a test per cell)**. **PHASE 1 COMPLETE:
  all four checks fire with zero flags in an onboarded repo; README quickstart samples are
  regenerated through the real pipeline.** *Polish noted, non-blocking: a gate ref that does
  not exist on GitHub renders as "couldn't reach GitHub"; a "this branch isn't on GitHub
  yet" line would be more precise.*
- **Phase 2, structural debt before breadth:** S6 registry consolidation (F5) **DONE
  2026-07-03 (merged `acd1779`, 471 tests; Opus 4.8 built in a worktree from the plan +
  rev-2 spec, Fable arbiter-reviewed with a per-worktree byte-identical render check; one
  registry owner `core/kinds.py`, copy completeness enforced at import)** · S7
  forge_review dual-card removal (F4) **DONE 2026-07-03 (merged `549f5d9`; codex built,
  Fable reviewed; collision copy has one home)** · S8 server-side path-filtered PR search +
  wire `incomplete[unbounded]` end to end (F7 + the truncation-copy follow-up).
- **Phase 3 = Sprint 3 proof:** labelled conformance corpus + replay harness + the E4/E5
  numbers; OpenRouter for model-diverse A/B arms.
- **Phase 4 = Sprint 4 breadth (goal expanded 2026-07-03):** S8 GraphQL collision + unbounded
  coverage **DONE (merged `a0bdc7d`, 541 tests; codex built from the twice-reviewed spec;
  live-smoked on real GitHub)** · S8b API-root seam **DONE (merged `0db294c`; Fable built,
  codex review caught the conftest isolation hole)** · S9a forge resolution + GitLab
  onboarder + honestly-unwired reporting **DONE (merged `a0f9f7d`, 598 tests; codex built
  and added a correct extra hardening commit the plan missed: a GitLab slug must never
  query GitHub Issues; Fable's arbiter smoke caught two copy bugs (duplicate note; the
  false-comfort "Looks clear" when NOTHING was checked, now "Nothing checked yet"))** ·
  S9b GitLab connector **DONE (merged `35f9fee`, 653 tests; live-smoked: real MR-worded
  green against a real project with a genuinely green pipeline)** · S10 Jira **DONE (merged
  `e060b18`, 715 tests; live-smoked: branch JIRAPLAY-1441-verify derived the real issue and
  fired field-level detail off the REAL stage changelog)** · S11 Confluence **DONE (merged
  `a405bee`, 761+ tests; Opus built, live read of space TS came back a real green; the CTO
  arbiter pass caught a cross-slice integration bug (a configured-Confluence family poisoned
  by the local-docs disabled note) and a two-round codex loop hardened the fix (status-aware
  docs failure copy: reached-but-incomplete vs unreachable)). **THE FOUR-SOURCE BROKER IS
  BUILT: GitHub, GitLab, Jira, Confluence, each live-verified.** Write targets verified
  live: Jira JIRAPLAY, Confluence TS. Lab repos seeded on both forges
  (teamctx-emulation-lab, private, controllable + slow CI).
- **Phase 5 COMPLETE 2026-07-04. Offline matrix: 12 of 12 PASS (`d33e62a`). LIVE PASS
  executed by the CTO across all four real sources (GitHub lab repo, GitLab lab project,
  the authorized Jira project + Confluence space): every scenario row live-verified, with
  the evidence corpus (redacted per the program map) + summary committed at
  `docs/validation/team-emulation-2026-07-04/`. The live run itself found and fixed a real
  copy bug (skipped GitLab pipelines claimed a connection problem; fixed on every surface,
  two-round adversarial review, merged `1f1652e`). Two named residuals, zero silent:
  live-unbounded (test-verified through the real pipeline) and real rate limiting
  (unit-verified). THE GOAL'S EXIT BAR IS MET: built, then tested like a team of
  people+agents across GitHub, GitLab, Jira, and Confluence, working as expected.**
- **Phase 5, team-emulation validation (goal set by Edgar 2026-07-03):** test teamctx like a
  team of people + agents working across GitHub, GitLab, Jira, and Confluence, and verify it
  all works as expected. Fable runs it: multiple emulated actors (separate clones/worktrees,
  distinct branches, real PRs/MRs/issues/pages), agent actors driven as subagents, scripted
  cross-actor scenarios per check (collision, criteria-changed, superseded doc, missed gate,
  each honest-UNKNOWN degradation), with expected-vs-actual surfacing recorded as evidence.
  This absorbs and extends the old "Edgar in N terminals" dogfood.

**Edgar checkpoints (his calls, at their moments):** ~~Atlassian credential~~ **RESOLVED
2026-07-03: `.secrets/jira-stage` (Atlassian Cloud API token, basic auth with Edgar's email)
against `https://stage-redhat.atlassian.net/`; read-verified live (whoami OK, 1742 Jira
projects visible, Confluence v2 spaces list OK). Never commit the URL or instance data into
repo fixtures (no Red Hat refs in the codebase).** ~~Jira project + Confluence space~~ **RESOLVED
2026-07-03 (Edgar authorized find-or-create; the instance is staging): Jira = project
JIRAPLAY (the instance's designated playground; create + field-level edit + close verified
live on JIRAPLAY-1441; NO delete permission, so artifacts are prefixed "[TCTX]" and closed
after each run) · Confluence = space TS "Testing spaces" (page create + delete full cycle
verified live). Conduct: clearly-labeled artifacts only, cleaned up after each run; real
keys never enter committed evidence (the redaction map covers them).** Remaining Edgar
inputs: PyPI publish · going public.

## The arc to product-complete (four sprints)

### Sprint 1: Effortless, correct invocation  *(DONE 2026-06-27: merged `85bded1`; 216 tests, ruff + mypy strict green)*
Resolve repo + branch + docs_root from git and a clean `.teamctx/config.json`
(precedence: `explicit > config > git-detect > honest-absent`). Fork false-all-clear closed
by config override; a genuinely missing repo gives a precise error, not an UNKNOWN wall.
Self-contained `work_start` config section; both transports resolve through one shared path.
Shared-committed (repo, docs_root) vs per-actor-local (token) seam kept clean, this is what
sets up Sprint 2's multi-actor emulation.
**Bar:** in a normal repo, `work_start(paths=[...])` alone returns correct collision + gate +
docs verdicts; forks correct via committed config; non-git / unreachable degrades to honest
-UNKNOWN; tests cover the UNKNOWN edges, not just the happy path.
Spec: `docs/superpowers/specs/2026-06-27-work-start-input-resolution-design.md`.

### Sprint 2: Ready for others, proven multi-actor  *(IN PROGRESS: M1 reflex + M2 messaging pass DONE 2026-06-28)*
pip/uvx installable; a real `teamctx init` that scaffolds the work_start config; MCP wiring +
file-based token hygiene documented; README that claims exactly what the code proves. **Retire
legacy:** drop `refresh`/`context`; rebuild `why`/`open-source` on the live broker. **Validation
= Edgar in multiple terminals emulating distinct actors** against a shared repo, we don't
recruit a human, we emulate humans, so the real cross-actor scenarios (collision / criteria /
doc / gate) surface correctly.
**Slice A, M1 (work_start as a reflex): DONE 2026-06-28 (merged `5bf4ad9`, 235 tests).** A
deterministic Claude Code `PreToolUse` hook (`teamctx-hook`: once-per-session, fail-safe
never-block, network time-bounded, edited path normalized to repo-relative so **no false
all-clear**) + opt-in `teamctx install-hook` + portable `CLAUDE.md` snippet. Signal model:
*ready / heads-up / can't-verify* (honest-UNKNOWN surfaces only when it changes the decision).
Spec/plan: `docs/superpowers/{specs,plans}/2026-06-27-m1-work-start-reflex*`.
**M2 (the messaging pass): DONE 2026-06-28 (merged `a41ad60`, 245 tests).** One shared `assess()`
classification (kind + per-check status, single source of truth incl. `IMPORTANT_CHECKS`) feeds both
the hook and a signal-led prose render (`render_broker_answer`), so every transport (CLI work-start,
MCP, probe commands, eval pack) speaks one plain voice. **Every check status is surfaced exactly once,
so honest-UNKNOWN is never silently dropped** (Checked / Couldn't check / Not checked lines; the final
review caught and we fixed three would-be silent-clear holes). Also a **repo-wide em-dash scrub**:
zero em dashes anywhere is now a hard ship gate ([[feedback_no_em_dashes_plain_human]]).
Spec/plan: `docs/superpowers/{specs,plans}/2026-06-28-m2-messaging-pass*`.
**Hardening, GitHub truncation honesty: DONE 2026-06-28 (merged `df58744`, 250 tests).** The PR probe
fetched only the first page of open PRs, a **false clear at the source** on busy repos. Now truncation
(PR list or any PR's files hitting the 100 page limit) sets a non-fresh source status, routing through
the existing closure to an honest UNKNOWN conflict verdict; a visible collision still fires. From
Edgar's 2026-06-28 review. Spec: `docs/superpowers/specs/2026-06-28-github-truncation-honesty.md`.
*Two sequenced follow-ups:* (1) precise truncation copy by wiring the reserved `incomplete[unbounded]`
reason (select.py) end to end, so it reads "checked the most recent N open PRs, more exist" instead of
routing through the M2 render's "couldn't reach GitHub" (touches core closure + assessment + render,
own slice); (2) path-filtered server-side PR search so very busy repos get a real conflict answer
instead of UNKNOWN.
**Sprint-2 build slices ALL DONE 2026-06-28/29:** B `init` (`8784ac3`) · C-surface dev namespace
(`2054f73`) · C-legacy snapshot retirement (`348c307`) · C-judge `why`/`open-source` on the live
broker (`16fbc36`) · D packaging (verified buildable via `python -m build`, publish parked) · E
README rewrite (`95b754a`). Plus both false-clear fixes (PR `df58744`, gate `c9e3e0c`) and token/clock
hygiene (`7e13ec7`). Autonomous-run trail: `docs/product/plan/AUTONOMOUS-LOG-2026-06-28.md`.
**Remaining for Sprint 2: the multi-actor dogfood** (Edgar in N terminals as distinct actors; needs a
human). **Parked for Edgar:** PyPI publish, going public.
**Carry-forward (non-blocking):** *Closed by M2*: the `gh pr view N` action (conflict findings now
carry it) and the stale Docs/Criteria honesty gap (now a "Couldn't check:" line). *Closed 2026-06-28
(`7e13ec7`)*: CLI now honors `{token_env}_FILE` via the shared `resolve_token`, and `_utc_now` is
deduped into `teamctx.clock.utc_now_iso`.
*New, for slice C*: the probe commands (`issue-probe` etc.) reuse the work-start render, so they print
"Looks clear to start." and not_configured reasons ("couldn't determine the repository/branch") that
read wrong for a single-check diagnostic; give the probes their own headline or suppress not-run
checks. **Bar:** fresh-actor setup from the README alone, and genuine multi-actor scenarios surfaced
correctly across terminals.
**Onboard + runtime-honesty slice (spec `docs/superpowers/specs/2026-06-29-onboard-runtime-honesty.md`,
hardened over a five-round codex loop): Phase 1 of 3 DONE 2026-06-29 (merged `3ad67c0`, 332 tests +
ruff + mypy strict green).** Closes the setup/runtime split-brain: a setup command must report exactly
what the runtime will do. Phase 1 = the shared resolution layer (`resolve_project_root`, host-aware repo
identity via `parse_github_repo` failing closed on non-github origins, `resolve_github_token` with a
`gh` fallback on the default env only); a codex diff-review caught three real split-brain P1s before
merge (`901ca4e`). **Phase 2 = the honesty carrier (spec 1.4 to 1.7): DONE 2026-07-01 (merged to
main via `feat/runtime-honesty-phase2`, 372 tests + ruff + mypy strict green).** Two additive v0
coverage states, `pending` (a gate whose checks are still running) and `not_applicable` (a docs root
scanned with nothing relied-on in scope), carried through `SourceStatusValue` + `Completeness` +
`assess_completeness` (evaluate/broker needed no change); the gate + docs connectors emit them and the
CLI render + hook surface them, total over every check so a status is never silently dropped. Plus
request-path normalization (a `./path` now matches), the "required" copy sweep, "CI is green" -> "no
failing checks found", init no longer auto-enabling `docs_root`, and a batch of fail-closed hardening
the codex loop drove: malformed check-runs payloads, non-passing conclusions (cancelled/stale), a
non-string conclusion, and absolute/symlinked docs roots all now fail closed instead of false-clearing.
Plan: `docs/superpowers/plans/2026-06-29-runtime-honesty-phase2.md`. **codex adversarially reviewed the
plan and then the diff across three rounds and found a real P0 (hook dropping a pending gate) plus
several genuine false-clears (a cancelled check reading green; a malformed payload dropping a failure)
that were all fixed before merge, which is exactly why the review-before-merge rule stands.** **Phase 3
= the visible `onboard` command (spec 2.x): DONE 2026-07-02 (merged to main via `feat/onboard-command`,
428 tests + ruff + mypy strict green), which COMPLETES the onboard + runtime-honesty slice.** `teamctx
onboard` scaffolds a repo with zero flags and zero false confidence: detect the GitHub repo, write a
trackable `.teamctx/config.json`, install the reflex hook, write an honest CLAUDE.md snippet (managed
between markers, migration-safe, never overwriting hand-edited content), report the real credential
path, and print a live open-PR reachability check that is never a verdict. **A single
`resolve_github_repo` is now shared by onboard and `resolve_work_start_inputs`, so the setup command
cannot report a different repo than the runtime resolves (the split-brain this slice refuses).** codex
adversarially reviewed the plan and then the diff across five rounds and found the marker-corruption P0,
the gitignore-parent-dir rule, and the onboard split-brain (repo-resolution parity), all fixed before
merge. **Next slice: auto-discovery (linked issue and `since` from branch/PR, the docs path-gating fix,
and expanding the snippet to claim all four checks); then GitLab and Jira plug the detect/registry
seam.**

### Sprint 3: Proof (the numbers)
Labelled conformance corpus + replay harness → the **E4/E5** numbers protocol v1.2 owes.
**Bar:** an evidenced statement of broker performance and honest-UNKNOWN behavior, the
quantified backbone of the "context ≠ memory / honest beats confident" claim the positioning
window rewards.

### Sprint 4: Breadth, venue-pulled
Second-source families with **real dogfood venues (confirmed: Jira + GitLab)**: Jira as a
second issue tracker, GitLab as a second forge, plus the deferred **linked-issue
auto-discovery** (parse issues from branch / PR / commits; derive `since`) so criteria becomes
automatic and source-plural.
**Bar:** a card from a new source changed a real decision in an actual venue.

### Beyond
Distribution / launch (teamctx.dev + the Kagenti/Rosso integration seed), CPO timing call,
after 1–3. Durable-memory package (Ambara lineage), deferred behind the evidence-vs-authority
seam.

## Supersedes (history; git holds the prior text)
- CURPLAN3 (MCP transport), done-gate met (Slice A shipped, Slice D dogfood passed).
- CURPLAN1 / CURPLAN2 / thesis-complete engine milestone, done (see `../sprints/`).
