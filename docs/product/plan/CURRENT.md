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
PRs), doc-superseded (frontmatter, merged 2026-06-20). **doc-superseded dogfood: not yet run.**
Positioning reframed to the ambient-team-context marquee.

## NOW → product-complete (rolling-wave: CP1 detailed, the rest coarse)

### CP1 — Marquee proven  *(NEXT — detail at sprint planning)*
Feed the two dormant engine kinds — connector-only work, no engine change:
- **missed-gate ← GitHub check-runs** (cheapest; reuses the wired GitHub auth)
- **criteria-changed ← Jira** (the headline "movement"; new work-tracker family)

Then the first real dogfood across ≥2 sources.
**Done when:** a card from a second source changes a real decision in a real session.

### CP2 — Ambient + breadth  *(coarse)*
The L (hint) tier behind a phantom-filter spike; Confluence + GitLab connectors.
**Done when:** ambient cards help without being noise (dogfooded).

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
