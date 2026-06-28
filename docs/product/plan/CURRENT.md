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

### Sprint 2: Ready for others, proven multi-actor  *(IN PROGRESS: Slice A / M1 reflex DONE 2026-06-28, merged `5bf4ad9`)*
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
**Remaining slices (ordered):** B `teamctx init` scaffolds the work_start config · C legacy
retirement (drop `refresh`/`context`, rebuild `why`/`open-source` on the broker) · D packaging
(pip/uvx) + token-hygiene docs · E README (claims-match-code, **reality-grounding** lead) · then the
multi-actor dogfood. **M2 (the messaging pass)** is the immediate copy slice (see
[[project_teamctx_surfaced_text]]).
**Carry-forward minors from M1 review (M2/later, non-blocking):** CLI `work-start` lacks the
`GITHUB_TOKEN_FILE` fallback the hook/MCP have; heads-up copy could name the `gh pr view N` action;
`_utc_now` is triplicated; a *stale* (tried-but-failed) Docs/Criteria source is currently neither
headlined nor in 'ready', fix when those checks join the headline set. **Bar:** fresh-actor setup from the README alone, and genuine multi-actor scenarios surfaced
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
