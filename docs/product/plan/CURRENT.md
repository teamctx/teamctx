# CURRENT — teamctx rolling plan

**This is the one current plan: NOW → product-complete (as currently known).** Read this
first, every session, and re-orient from it before acting. It is regenerated at each
checkpoint; superseded versions move to `previous/`. Deep detail lives *below* it via the
links (progressive disclosure), never inline.

- **Gap + phase detail:** [product-completion-plan](../sprints/2026-06-21-product-completion-plan.md)
- **Decided positioning (the marquee):** [positioning](../vision/positioning.md)
- **Landscape: agent-memory wave:** [landscape note](../../research/landscape-agent-memory-2026-06.md)
- **Live vs deferred connectors:** [connector-status](../../engineering/connector-status.md)

**How this doc stays current (the ritual):**
- **One plan in flight (WIP = 1).** When a checkpoint's done-gate is met, regenerate this file
  (re-detail the next checkpoint, re-sketch the rest); move the old copy to `previous/`.
- **Trigger:** the replan rides the green merge-to-main that closes a vertical — replan *before*
  starting the next, not from memory.

---

## Urgency context (2026-06-25)

The agent-memory wave is peaking — RH ET published "From context to dreams" (Jun 1, 2026),
the industry is converging on probabilistic memory as the default agent-context solution.
teamctx's deterministic, trust-grounded positioning is **differentiated but only if it
ships.** The window to establish "context ≠ memory" as a category is open now. See
[landscape note](../../research/landscape-agent-memory-2026-06.md) and the updated
[positioning](../vision/positioning.md) differentiation section.

## Where we are (NOW — 2026-06-25)

Engine complete (4 card kinds; T1/T2/T5/S2 in code). **3 connectors live:** collision
(GitHub PRs), doc-superseded (frontmatter), missed-gate (GitHub check-runs). CI on
teamctx itself (GitHub Actions: pytest + ruff + mypy).

**CURPLAN1 COMPLETE (2026-06-25).** `feat/missed-gate-connector` merged to main. Dogfood
ran: pushed a deliberately-failing test → CI went red → `gate-probe` surfaced
"Required gate 'check' is failing on this branch" + `Gate check: NOT CLEAR` →
card changed the decision (fix CI before proceeding). All 3 slices done.

**Shipped cross-cutting (off the CURPLAN ladder), on `main`:** protocol paper v1.2
(soundness scoped to `deps_G` via O1a/O1b, side-channel discipline, consumer conformance).
Landing page (`site/`) on Vercel — **teamctx.dev live pending DNS `A` record**
(see [launch-readiness](../launch-readiness.md)). Agent-memory landscape analysis +
positioning differentiation section added (2026-06-25).

**Open obligation (from v1.2):** measured **E4/E5** numbers (false-`Unknown` rate; consumer
false-clear rate) — defined + bounded in the paper but not yet measured; needs the
conformance-corpus replay harness.

## NOW → product-complete (rolling-wave: CURPLAN2 detailed, the rest coarse)

### CURPLAN2 — Criteria movement + ambient breadth  *(NEXT UP)*
- **criteria-changed via the work-tracker family** — instantiate **GitHub Issues first**
  (dogfoodable, reuses GitHub auth); **Jira** is the same family's second provider (the
  sales headline), live when there's a venue.
- The **L (hint) tier** behind a phantom-filter spike; Confluence + GitLab connectors.
**Done when:** a second-source movement card (issue / ambient) changes a real decision.

### CURPLAN3 — Consumable  *(coarse)*
MCP transport (harvest Jurati) + warm daemon; keep the file/CLI bridge for non-MCP agents.
**Done when:** an agent consumes teamctx over MCP in a real session.

### CURPLAN4 — Ready for others  *(coarse)*
Source-integration pipeline (auth broker, permission filter, cache) as multi-user demand
appears; release gates (README / pip / security-privacy docs matching impl).
**Done when:** someone other than the maintainer runs it end-to-end.

### Later / optional
Durable memory (2nd package, Ambara lineage), behind the evidence-vs-authority seam.

---

## Supersedes (now "previous" — kept as history, not deleted)
- CURPLAN1 missed-gate vertical (DONE 2026-06-25) — merged `feat/missed-gate-connector`
- Thesis-Complete Engine milestone (DONE) — `../sprints/2026-06-19-milestone-thesis-complete-engine.md`
- State & Plan, 2026-06-18 pre-build snapshot — `../vision/state-and-plan.md`
- Sprint 01 / 02 / 03 plans — `../sprints/2026-06-16-*`, `../sprints/2026-06-19-sprint-03.md`
