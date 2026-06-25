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

## NOW → product-complete (FOUNDATION HARDENING done; MCP is next up)

### FOUNDATION HARDENING — COMPLETE (2026-06-25, merged to main)

**Edgar's call: stop forward motion, make the base excellent before MCP.** The code review
found two structural problems under the green tests: (1) two parallel models in `core/` (real
contracts model + retired prototype) so the automated evidence engine validated a stand-in;
(2) missing compose seam — `work-start` was collision-only. Both fixed across five phases,
green at each step, merged to main (`2f183df`):
- **ONE model** — prototype + prototype-coupled campaign deleted (~1450 lines); evidence engine
  rebuilt on the real broker (`eval/`), so the A/B context arm IS the live product output.
- **Broker entry point + compose seam** (`core/broker.py`); **unified `work-start`** runs all
  connectors (`runner.py`); verdict logic in one place.
- Clean seams: shared connector helpers, render de-dup, `py.typed`, tests linted in CI.
- 180 tests, ruff(src+tests) + mypy strict + purity green; CI verified.

Full record: [2026-06-25-foundation-hardening.md](../sprints/2026-06-25-foundation-hardening.md).
**E4/E5 harness** deferred to normal mode (needs a labelled corpus = the research campaign).

### CURPLAN3 — Consumable: MCP transport  *(NEXT UP — build on `broker_answer`)*
MCP server so agents consume teamctx programmatically (not manual CLI). The foundation gives a
clean base: the MCP `work_start` tool wraps `runner.run_work_start_connectors` →
`broker_answer_from_documents` → `render_broker_answer` — the same path the CLI uses, no
transport-adapter hack. **Done when:** an agent consumes teamctx over MCP in a real session.

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
