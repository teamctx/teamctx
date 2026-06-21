# CURRENT — teamctx rolling plan

**This is the one current plan: NOW → product-complete (as currently known).** Read this
first, every session, and re-orient from it before acting. It is regenerated at each
checkpoint; superseded versions move to `previous/`. Deep detail lives *below* it via the
links (progressive disclosure), never inline.

- **Gap + phase detail:** [product-completion-plan](../sprints/2026-06-21-product-completion-plan.md)
- **Decided positioning (the marquee):** [positioning](../vision/positioning.md)
- **Live vs deferred connectors:** [connector-status](../../engineering/connector-status.md)

**How this doc stays current (the ritual):**
- **One plan in flight (WIP = 1).** When a checkpoint's done-gate is met, regenerate this file
  (re-detail the next checkpoint, re-sketch the rest); move the old copy to `previous/`.
- **Trigger:** the replan rides the green merge-to-main that closes a vertical — replan *before*
  starting the next, not from memory.

---

## Where we are (NOW — 2026-06-21)
Engine complete (4 card kinds; T1/T2/T5/S2 in code). **2 connectors live:** collision (GitHub
PRs), doc-superseded (frontmatter, merged 2026-06-20). **CP0 dogfood: demo ran on model-citizens
(comedy-engine spec → generation-bottleneck note) — card renders, names the current doc, verdict
fires; real-session verdict + permanent install pending Edgar's confirm of the target.**
Positioning reframed to the ambient-team-context marquee.

## NOW → product-complete (rolling-wave: CP1 detailed, the rest coarse)

### CP1 — Marquee proven: the missed-gate vertical on teamctx  *(NEXT)*
teamctx has no CI and we don't use Jira, so the only dogfoolable second source right now is CI on
teamctx itself. Rescoped to one finishable vertical (criteria-changed/Jira → CP2):
- **Slice A:** add CI to teamctx (GitHub Actions: pytest + ruff + mypy) — prerequisite + overdue; creates the check-run source.
- **Slice B:** `missed-gate ← GitHub check-runs` connector (reuses GitHub auth). Spike: `scope["files"]` = the branch/PR changed files the gate ran against (engine intersects with your paths).
- **Slice C:** dogfood on teamctx — a red-CI card on files you're touching changes what you do.

**Done when:** a missed-gate card changes a real decision in a real teamctx session.

### CP2 — Criteria movement + ambient breadth  *(coarse)*
- **criteria-changed via the work-tracker family** — instantiate **GitHub Issues first** (dogfoolable, reuses GitHub auth); **Jira** is the same family's second provider (the sales headline), live when there's a venue.
- The **L (hint) tier** behind a phantom-filter spike; Confluence + GitLab connectors.
**Done when:** a second-source movement card (issue / ambient) changes a real decision.

### CP3 — Consumable  *(coarse)*
MCP transport (harvest Jurati) + warm daemon; keep the file/CLI bridge for non-MCP agents.
**Done when:** an agent consumes teamctx over MCP in a real session.

### CP4 — Ready for others  *(coarse)*
Source-integration pipeline (auth broker, permission filter, cache) as multi-user demand
appears; release gates (README / pip / security-privacy docs matching impl).
**Done when:** someone other than the maintainer runs it end-to-end.

### Later / optional
Durable memory (2nd package, Ambara lineage), behind the evidence-vs-authority seam.

---

## Supersedes (now "previous" — kept as history, not deleted)
- Thesis-Complete Engine milestone (DONE) — `../sprints/2026-06-19-milestone-thesis-complete-engine.md`
- State & Plan, 2026-06-18 pre-build snapshot — `../vision/state-and-plan.md`
- Sprint 01 / 02 / 03 plans — `../sprints/2026-06-16-*`, `../sprints/2026-06-19-sprint-03.md`
