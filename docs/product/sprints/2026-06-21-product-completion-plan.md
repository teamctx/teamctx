# Product Completion — Gap & Build Plan

*Dated 2026-06-21. Where we are after the [thesis-complete engine milestone](2026-06-19-milestone-thesis-complete-engine.md)
(the credibility **because** is built) and where we go to build the **marquee** — the rest
of the product. Companion to [positioning.md](../vision/positioning.md) (the decided
category), [state-and-plan.md](../vision/state-and-plan.md) (the decided spine),
[build-plan.md](../../engineering/build-plan.md) (source sequencing), and
[source-integration-layer.md](../../engineering/source-integration-layer.md). Bar: claims
never outrun proof — every item tagged **built / decided / open**.*

---

## 1. The gap (decided vs built)

The engine milestone built the **certified core** — the credibility *because*. The decided
product (`positioning.md`, 2026-06-19) is a much larger thing: **timely, ambient team
context** across many sources. What's built is the provable minority slice on two sources.

**Quantified, from our own measurement** (`state-and-plan.md §3`, relevance-coverage
experiment): structural/certified relevance **S ≈ 38%** of high-value events · untrusted-hint
**L ≈ 43%** · declared **D ≈ 18%**. We deliberately built the certifiable **S** slice first;
the largest slice (**L**, the ambient awareness) is a reserved-but-empty channel.

| Decided capability | Built today | The gap |
|---|---|---|
| **Marquee: ambient team context** (`positioning.md`) | Card-delivery rail + 2 sources | breadth + the ambient tier (below) |
| **Sources**: GitHub · GitLab · Jira/Linear · Confluence · Slack · local-notes · CI (`source-integration-layer.md`, `build-plan.md`) | **GitHub PRs + repo docs** (2 of ~7) | GitLab (type stub only), **Jira / Confluence / Slack / CI = none live** |
| **Relevance tiers S / D / L** (`state-and-plan §2.7`) | **S** built; D = behavior only; **L = empty** | the **L "untrusted hint" tier has zero producers** (`Hint` type exists, `hints=()` always) — the 43% slice |
| **Card kinds** (4, engine-complete) | 4 in engine; **2 live** (collision, doc-superseded) | **criteria-changed + missed-gate kinds exist but have no live connector** |
| **The credibility engine** (the *because*) | **Built** — T1/T2/T5/S2 in code | ~complete ✓ |
| **Transport: file + CLI + MCP** (`state-and-plan §2.3`) | **file + CLI** | **no MCP** (the Jurati machine plane), no IDE panel |
| **Source-integration pipeline** (`source-integration-layer.md`) | thin: connector fetch + normalize | no auth broker, no per-dev impersonated OAuth, no artifact cache, no relationship builder, partial policy firewall |
| **Authority** declared records (`arch-decision #6`) | behavior (resolved/missing/refuse-to-pick) | graduated `.teamctx`→durable, temporary-override states |
| **Phantom filter** (alert-fatigue cure) · **warm daemon** (latency fix) | neither | unbuilt; the ~4s "honesty tax" (`state-and-plan §3`) is unfixed |
| **Durable memory** (2nd package, Ambara) | not built | deferred **by design** ✓ (not a gap) |

**Honest verdict.** *Sequenced, not missed.* Building the provable core first was the right
call (it's the proof obligation and the hardest to retrofit). But the gap is now large enough
that **the product does not yet demonstrate its own headline** — and the dogfood we queued
(doc-superseded) tests the *gate*, not the *ambient broker*.

---

## 2. Build principles (the discipline this plan runs under)

1. **Usefulness-gated.** A vertical isn't done until a card changed a real decision in a real
   session. Breadth is not built on an unproven base. (See `connector-status.md`.)
2. **One finishable vertical at a time**, green-CI as the handoff. No big-bang.
3. **Map the whole, detail only the next 1–2 sprints.** Distant phases stay coarse — detailed
   plans are written (via the writing-plans skill) only when a sprint starts.
4. **Breadth before pipeline-depth.** Don't build the enterprise auth/permission/cache
   pipeline until multi-user demand is real; env-token + the existing policy firewall suffice
   for solo/single-user dogfooding.
5. **Harvest, don't re-derive.** MCP from Jurati; the source order from `build-plan.md`; the
   Route/Stamp/Envelope, phantom-filter, and authority designs from `state-and-plan.md` /
   `architecture-decision.md`.
6. **Lead the marquee; keep the *because* as the trust anchor**, not the headline.

---

## 3. The forward map (phased; coarse on purpose past Phase 1)

### Phase 0 — Prove the current vertical *(gates everything)*
Run the doc-superseded dogfood on a real repo (model-citizens). Decide its verdict, and
decide whether the dogfood from here on rides the **marquee** (a Jira/PR-movement moment)
rather than the gate. **No new breadth ships until one card has changed one real decision.**

### Phase 1 — Marquee breadth, certified-first *(highest leverage: the engine already supports it)*
The engine has 4 card kinds; only 2 are fed. Feeding the other two is **connector-only work**
— near-zero engine change, doubles the live surface.
- **missed-gate ← GitHub check-runs** — cheapest: reuses the wired GitHub auth; engine kind exists.
- **criteria-changed ← Jira (work-tracker family)** — highest value: the "movement in Jira" the
  product promises; engine kind exists; new family, proven forge-review pattern to mirror.
- **Confluence (docs/process family)** — authority/process-doc movement; the day-in-the-life scenes.
- **GitLab (forge-review 2nd provider)** — cheap once the family contract is exercised.

### Phase 2 — The L (hint) tier *(the 43% ambient slice — the real marquee)*
- **Phantom filter first** — the deterministic relevance/alert-fatigue discipline (`state-and-plan §2.7`);
  the 0.44-precision lesson means ambient signals stay **L, never certified**.
- **L producers**: PR / issue / doc *movement in your area* (not just exact-path conflicts),
  uncertified and clearly labeled. This is the awareness layer that makes "the same live picture" real.
- **The L→D flywheel** — honest "Unknown" nudges teams to declare tribal knowledge.

### Phase 3 — Distribution / consumption *(open-item #9: "under-built for distribution")*
- **MCP transport** (machine plane; harvest Jurati) + keep the file/CLI bridge for non-MCP agents.
- **Warm daemon + freshness-stamped cache** — erases the latency tax (~4s → ~8ms); "stateless ≠ no cache."
- **IDE panel** (human plane) — later.

### Phase 4 — Pipeline & multi-user hardening *(only as enterprise demand appears)*
- Source Integration Layer proper: auth broker · permission filter (per-dev impersonated OAuth)
  · full policy firewall (redaction/PII/injection/sensitivity) · artifact store/cache · relationship builder.
- Authority: graduated declarations (`.teamctx`→durable) · temporary-override states.

### Phase 5 — Durable memory (2nd package, Ambara) *(behind the seam; optional; last)*

**Cross-cutting (not a phase):** positioning copy against a real page · release gates
(README / pip / security-privacy docs matching impl) · deferred sources (Slack handoffs, local
notes/Obsidian) when their marker/allowlist rules are proven.

---

## 4. Open sequencing calls (decide at sprint planning)
- **Jira-first vs GitLab-first.** `build-plan.md` ordered GitLab earlier (cheap, same family);
  value says Jira (activates the dormant criteria-changed kind + the headline "movement"). **Recommend Jira.**
- **Does doc-superseded dogfood still run standalone, or fold into a Phase-1 marquee dogfood?**
- **L-tier relevance discipline** needs a phantom-filter spike before any L producer ships.

## 5. Explicitly not now
Big-bang build · detailed plans for Phases 3–5 · the durable layer before breadth proves out ·
the full enterprise pipeline before multi-user demand is real.
