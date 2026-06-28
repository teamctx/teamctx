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
**Remaining slices (ordered):** B `teamctx init` scaffolds the work_start config · C legacy
retirement (drop `refresh`/`context`, rebuild `why`/`open-source` on the broker) · D packaging
(pip/uvx) + token-hygiene docs · E README (claims-match-code, **reality-grounding** lead) · then the
multi-actor dogfood.
**Carry-forward (non-blocking):** *Closed by M2*: the `gh pr view N` action (conflict findings now
carry it) and the stale Docs/Criteria honesty gap (now a "Couldn't check:" line). *Closed 2026-06-28
(`7e13ec7`)*: CLI now honors `{token_env}_FILE` via the shared `resolve_token`, and `_utc_now` is
deduped into `teamctx.clock.utc_now_iso`.
*New, for slice C*: the probe commands (`issue-probe` etc.) reuse the work-start render, so they print
"Looks clear to start." and not_configured reasons ("couldn't determine the repository/branch") that
read wrong for a single-check diagnostic; give the probes their own headline or suppress not-run
checks. **Bar:** fresh-actor setup from the README alone, and genuine multi-actor scenarios surfaced
correctly across terminals.

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
