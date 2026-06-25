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

Engine complete (4 card kinds; T1/T2/T5/S2 in code). **All 4 certified card kinds have
live connectors:** collision (GitHub PRs), doc-superseded (frontmatter), missed-gate
(GitHub check-runs), criteria-changed (GitHub Issues). CI on teamctx itself (GitHub
Actions: pytest + ruff + mypy). 212 tests.

**CURPLAN1 COMPLETE (2026-06-25).** `feat/missed-gate-connector` merged to main. Dogfood:
red CI → `gate-probe` surfaced "Required gate 'check' is failing" + `Gate check: NOT CLEAR`.

**CURPLAN2 COMPLETE (2026-06-25).** `feat/issue-criteria-connector` merged to main. Dogfood:
edited issue #2 body + added label + closed → `issue-probe` surfaced "Issue #2 updated:
state is now closed; labels now: dogfood" + `Criteria check: NOT CLEAR`. Connector detects
body edits, state changes, and label changes since a reference timestamp.

**Deferred from CURPLAN2 scope (pull when needed, not blocking):**
- **Jira** as second issue-tracker provider (the enterprise sales headline; no venue to dogfood)
- **L (hint) tier** — the 43% ambient awareness slice; needs phantom-filter spike first
- **Confluence / GitLab** connectors — more breadth, lower urgency

**Shipped cross-cutting (off the CURPLAN ladder):** protocol paper v1.2 · landing page on
Vercel (teamctx.dev live pending DNS `A` record) · agent-memory landscape analysis +
positioning differentiation.

**Open obligation (from v1.2):** measured **E4/E5** numbers — needs conformance-corpus
replay harness.

## NOW → product-complete (rolling-wave: CURPLAN3 detailed, the rest coarse)

### CURPLAN3 — Consumable: MCP transport  *(NEXT UP)*

teamctx is currently CLI-only. For the "context for agents" positioning to be real, agents
need to consume it programmatically — not through a human running a shell command. MCP is
the integration standard the ecosystem is converging on.

**What:** MCP server exposing teamctx probes as tools. An agent calls `work-start` (or
individual probes) via MCP and gets the context cards + verdict as a tool result.

**Harvest:** Jurati v1 had an MCP implementation — reuse the transport plumbing, not the
old context model. The CLI already has the probe → render pipeline; MCP wraps it.

**Slices (to be detailed at sprint start):**
- **Slice A:** MCP server skeleton — expose `work-start` as a tool (combines collision +
  doc-superseded + missed-gate + criteria-changed probes, renders the unified view)
- **Slice B:** Individual probe tools (`gate-probe`, `issue-probe`, `docs-probe`,
  `github-pr-probe`) for targeted queries
- **Slice C:** Warm daemon + config — persistent process that agents connect to, reads
  `.teamctx/config.json` for defaults (repo, token, etc.)
- **Slice D:** Dogfood — an agent (Claude Code or OpenClaw) consumes teamctx over MCP in a
  real session, and the context changes a decision

**Done when:** an agent consumes teamctx over MCP in a real session.

### CURPLAN4 — Ready for others  *(coarse)*
Source-integration pipeline (auth broker, permission filter, cache) as multi-user demand
appears; release gates (README / pip / security-privacy docs matching impl).
**Done when:** someone other than the maintainer runs it end-to-end.

### Breadth (pull when venue exists)
- Jira (issue-tracker family, 2nd provider) · Confluence (docs family) · GitLab (forge-review
  family, 2nd provider) · the L hint tier (phantom-filter spike first)

### Later / optional
Durable memory (2nd package, Ambara lineage), behind the evidence-vs-authority seam.

---

## Supersedes (now "previous" — kept as history, not deleted)
- CURPLAN2 criteria-changed connector (DONE 2026-06-25) — merged `feat/issue-criteria-connector`
- CURPLAN1 missed-gate vertical (DONE 2026-06-25) — merged `feat/missed-gate-connector`
- Thesis-Complete Engine milestone (DONE) — `../sprints/2026-06-19-milestone-thesis-complete-engine.md`
- State & Plan, 2026-06-18 pre-build snapshot — `../vision/state-and-plan.md`
- Sprint 01 / 02 / 03 plans — `../sprints/2026-06-16-*`, `../sprints/2026-06-19-sprint-03.md`
