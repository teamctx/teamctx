# teamctx — State & Plan (session capture, 2026-06-18)

*Where we are, what we decided and learned, what's open, and where we go next.
Companion to the [architecture decision record](architecture-decision.md), the
**consolidated [protocol paper v1.0](../../research/teamctx-protocol-v1.0.md)**
(supersedes the v0.1–v0.5 sequence), and the vision artifacts
([day-in-the-life](day-in-the-life.md), [personas](personas.md)). This closes a deep
vision-and-formalization push; we are at a deliberate stopping point before build.*

---

## 1. What teamctx is (settled)

A **deterministic, no-LLM, read-only, cross-agent context broker** for AI coding
agents. At work-start (new branch / resumed session) any agent — Claude Code, Codex,
Gemini CLI, Cursor, opencode — asks for context and gets compact, typed,
permission-scoped **context cards** plus an honest **coverage certificate**. One
decision (no LLM in the core) buys four otherwise-conflicting properties:
token/wasted-work savings, can't-track (by non-retention), bounded harm (read-only +
deterministic selection), cross-agent portability (context is data).

**The full-circle finding.** A fresh-eyes derivation reconverged on Edgar's original
**Jurati MCP** design — now with a proof scaffold under it. The detour's payoff was
not the architecture (Jurati had it) but discovering the **seam**: the broker's read
half can make provable guarantees the durable half structurally cannot.

---

## 2. The decisions (the v0 spine)

Full detail in [architecture-decision.md](architecture-decision.md). Seven decisions:

1. **Two packages, one product** — stateless broker (base) + optional durable memory
   layer. The seam is **evidence vs. authority** (= stateless vs. durable): they make
   opposite promises about state and must be separate record types. Capability-absence
   is **SBOM-auditable** (durable code not in the lockfile). Capability **ladder**:
   credential → **egress + connector allowlist (load-bearing rung)** → dependency →
   package/process. Strict one-way coupling; durable registers as *just another read
   source*; broker stays stateless even when memory is present. Broker is an
   **extraction** from the shared pure foundation, not a rewrite.
2. **Product *and* protocol** — standardize the edges (card schema, coverage
   certificate, connector interface, transport); own a single canonical reproducible
   **engine**; no third-party engines in v1 (determinism would drift).
3. **Cross-agent transport** — file + CLI + MCP. The **file adapter** is the
   plugin-free, per-everything foundation (stronger than an IDE plugin). **Two planes:**
   machine (MCP→agent, delivers value) + human (file/CLI/IDE-panel, delivers trust),
   the human plane **renders certified cards directly, never via the LLM**, and
   **prints, never blocks**.
4. **Route / Stamp / Envelope** — every candidate claim → ROUTE (surface? how loud?
   which tier? — **tunable**), STAMP (honest framing — **fact, never tunable**),
   ENVELOPE (coverage). Composition **algebra**: gate / multiplicative-precondition /
   additive-flavor / interaction / categorical-state — *intersections are computed,
   not enumerated*. **Trust tiers** certified|hint are a **firewall**. **Tune the
   gate, never the truth.** Two failure families (cry-wolf / lie); **trust is
   multiplicative** (one bad card poisons the surface).
5. **Severity** = deterministic cost-of-not-knowing = `clamp01(kind_base × (1 +
   α·magnitude) × scope_mult)`. Magnitude (fan-out) ≠ relevance (proximity). Tunable
   (kind table, α, scope) vs. fixed (magnitude is a graph fact). Keeps its
   decomposition for the `why`/audit.
6. **Authority** as a first-class **declared** record (resolved/missing/conflicted/
   temporary). Behavior (refuse-to-pick, surface-conflict) is core; declarations are
   graduated (`.teamctx` → durable layer). Suppress-agreement / demote-dissent.
   *Extends the protocol → v0.5.*
7. **Relevance is structural-by-design** (S certified / D declared / L untrusted-hint).
   **Rock-solid = honest coverage, not total coverage.** The **L→D flywheel** (the
   broker's honest "Unknown" nudges teams to write tribal knowledge into linked/declared
   artifacts). **Phantom filter** (diagnostic vectors) = deterministic alert-fatigue cure.

**Honesty invariants (hard lines):** read-only; can't-track by non-retention;
absence ≠ clearance; fidelity ≠ truth; deterministic/replayable; tune-the-gate-never-
the-truth; no people-graph; bounded-harm honestly scoped (not "incapable of harm").

---

## 3. What we proved / measured this session

- **Protocol v0.5** (authority primitive, certified-set restriction T7, diagnostic-
  vector classification T3″) written and refereed through **two rounds** by a 4-model
  panel: round-1 minor/major → all six convergent bugs fixed → round-2 **accept-with-
  nits**, all six confirmed closed, one new pigeonhole (budget vs. dissent) resolved
  via `Unknown[truncated]`. (Mirrors the v0.1→v0.4 Reject→Accept arc.)
- **Latency experiment** — the "honesty tax" is real for the naive design (~4s p95)
  but the **warm-daemon + freshness-stamped cache** design erases it (~8ms p95); cost
  moves to staleness, which the certificate reports. "Stateless" = no durable *trusted*
  state, **not** no cache.
- **Relevance-coverage experiment** — structural relevance covers ~**38%** of high-
  value events (L≈43%, D≈18%); but it's the certifiable, highest-confidence,
  costliest-to-miss slice. Validates structural-by-design + the L→D flywheel.
- **Disagreement-detection experiment** — two deterministic detectors hit **precision
  0.44** on a 48-item adversarial corpus → undeclared value-disagreement **stays an L
  hint, not a certified card**. The integrity thesis eating its own dogfood.

All artifacts persisted under
[`docs/research/reviews/arch-panel-2026-06-18/`](../../research/reviews/arch-panel-2026-06-18/).

---

## 4. Open items (named, not hidden)

| # | Item | Status |
|---|---|---|
| 1 | φ-robustness (A4) | partially answered (extraction brittle → keep certified surface structural / pinned-typed) |
| 2 | Undeclared-disagreement certifiability | **RESOLVED** — stays L hint (precision 0.44) |
| 3 | Severity calibration | **deferred by nature** — needs deployment telemetry; defaults are sane starting guesses |
| 4 | Protocol v0.5 formalization | **DONE** (round-2 closed) |
| 5 | T3″ non-interference lemma + mechanized proofs | proof obligations, non-blocking |
| 6 | SRE / operability persona | **DONE** — Nadia (operator-of-daemon): fail-safe read-only, bounded egress, back-off → honest-staleness, replay forensics; freshness-as-SLO the honest limit ([personas.md](personas.md) §7) |
| 7 | Safe-experiment harness | **open** — sandbox + guardrails for poisoned-source tests (no unsafe experiments) |
| 8 | Vision artifacts vs. new model | **partial** — Wei + Nadia personas written against the v0 model (authority/operability); day-in-the-life + the original Raj/Priya/Sol personas still predate Route/Stamp + the disagreement downgrade |

---

## 5. Where we go next (prioritized)

**Still in the vision phase (no code yet, per Edgar's framing):**
1. **Reconcile the vision artifacts** (day-in-the-life, personas) with the v0 model —
   authority cards, Route/Stamp, the human plane, disagreement-as-hint. ✅ **Staff/
   Principal-Engineer (Wei)** and **SRE/operability (Nadia)** personas written
   ([personas.md](personas.md) §6–§7, against the v0 model); the original Raj/Priya/Sol
   personas + day-in-the-life still need the Route/Stamp + disagreement-downgrade pass.
2. **Spec the safe-experiment harness** (#7) — sandbox + guardrails (verify real
   tooling before any agent-under-attack test; untrusted payloads only ever touch the
   deterministic broker in golden tests, or a sealed disposable sandbox).
3. Optionally complete the **full role-play panel** (CPO/CTO/eng/business) — partially
   covered by the architecture/referee panels.

**When build starts (the first moves):**
4. **Extract the `teamctx` broker** from the shared pure foundation (core + read
   connectors + transports), omitting durable/write code → the capability-absent base
   package.
5. **Publish the contract spec** (card schema, coverage certificate, connector
   interface, transport) — the standardized edges.
6. **Implement** Route/Stamp/Envelope + the coverage taxonomy + the phantom filter +
   authority *behavior* (missing-default / refuse-to-pick / surface-conflict). Severity
   defaults shipped, calibrated later via dogfood telemetry.

---

## 6. How we worked (methodology that earned its keep)

- **Frontier panels + counter-panels** (gpt-5.1, gemini-3.1-pro, deepseek-v4-pro via
  OpenRouter; gpt-oss-120b via Cerebras; local codex/gemini as counter-panel),
  product-only guardrail enforced.
- **The referee loop** as a convergence engine (Reject→…→Accept), repeated for the
  v0.5 extension. New formal primitives are unproven until refereed; the panel
  reliably catches internal contradictions.
- **Small experiments to adjudicate disagreements** (latency, relevance, disagreement-
  detection) — modeled/adversarial, honest about "direction not exact %."
- **Cross-product pattern-matching** as compression (gut-pulls cheap to check;
  occasionally a key — but **80%-right analogies are the expensive trap**; the
  *tune-the-gate-never-the-truth* boundary came from catching one such disanalogy).
- **Claims never outrun proof** — every decision tagged proven / decided / open.

**Private prior art (do NOT cite in teamctx product/vision docs):** the assurance-
state-model pattern and the pure-core/tuned-weights house pattern were sharpened by
two of Edgar's other projects (one unshipped). They are internal lineage and
borrowable code, not a public reference.

---

## 7. Standing context

- **Edgar's frame:** building a **product** (OSS, maybe acquired), not a company.
  Evaluate on adoption / trust / impact — **not** business model / pricing / GTM.
- **Deployment model & cloud-vs-self-hosted sources:** left **open** (not locked).
- **Connectors first-class:** GitHub, GitLab, Jira, Confluence. **No in-editor LLM
  assistant** (the IDE *panel* is a deterministic renderer, a different thing).
- **Reusable harness** lives in `/tmp/teamctx-arch-panel/` (panel + experiment
  scripts); secrets at `~/.secrets/{openrouterkey,cerebras}`; Cerebras needs a browser
  User-Agent to bypass Cloudflare 1010.

---

## 8. v1.0 paper revisions (Edgar's review, 2026-06-18) — ✅ ALL FIVE APPLIED

**Status:** all five landed in `teamctx-protocol-v1.0.md` (next session resumed):
#1 `deps_G` → explicit `complete?` checker + obligation **O1** (§5; T2/T4 now stated
*under O1*); #2 `H` declared outside the privacy contract, projected to `Δ_P` if
surfaced (§4/§6); #3 T1 reworded to *verifiable replay* + content-addressed snapshot
(§4); #4 source-indexed freshness + stale-high/fresh-low → `Unknown[unobserved]` with a
worked example (§8); #5 certificate schema + a full worked trace (Appendix A).
**Re-refereed (2 rounds) → CLOSED.** Round 1 caught two real defects the fixes
introduced/exposed — a δ-bypass privacy leak (closure status in κ) and a polarity bug
(universals mis-valued); both fixed (δ-gated closure; shape-branched valuation with
`Unknown[conflicting-evidence]`). Round 2: gpt-5.1 **accept**, gemini accept-w-minor,
deepseek minor — the two prescribed fixes applied, paper closed. Reports
`v10r1_*` / `v10r2_*`. Remaining proof obligations (non-blocking): T8 non-interference
lemma, mechanization. Original review preserved below.

Edgar's own referee pass on [`teamctx-protocol-v1.0.md`](../../research/teamctx-protocol-v1.0.md).
What he liked: the four-pain-point framing; the explicit non-novelty humility (§3); the
certified-`C` / untrusted-`H` boundary; the extraction-limit section using bad precision
*as a design argument* rather than waving it away. Five fixes, roughly in priority:

1. **`deps_G` is carrying too much theorem weight (the load-bearing fix).** Observable
   soundness (T2) depends on the consumer verifying `deps_G(ρ)` is *complete* — right now
   that rigor hides in the word "conservative." Make **`deps_G` / completeness its own
   explicit certificate object or checker, with stated failure modes**, or a skeptical
   reader says "the whole soundness theorem moved into one adjective."
2. **Pin the security status of `H` under the privacy contract.** `H` is uncertified
   (§4) but T5's observable is only `⟨C, κ⟩` (§6). State it explicitly: either **`H` is
   outside the privacy contract**, or **`H` must also be computed from the
   consumer-visible projection** (else `H` can leak invisible existence).
3. **T1 overstates replay.** A digest *binds* a snapshot; it doesn't *enable replay*
   unless the snapshot/archive is retrievable. Reword to "enables **verification** of
   replay," or include a **content-addressed snapshot reference**.
4. **Tighten the authority-state rules (§8).** `E=fresh` should be **source-indexed**;
   the stale/`⊥` override behavior needs a **worked example** — esp. the policy-sensitive
   case: *stale high-priority authority + fresh lower-priority authority* → does it
   resolve downward, or become `Unknown[unobserved]`? Decide and show it.
5. **Add a concrete certificate schema + one worked example (S1 or S2).** Input
   observations → emitted cards → emitted `κ` → consumer result. This turns it from "a
   paper about a system" into "a protocol someone can implement." *(Highest-value
   *addition*, vs. 1–4 which are *fixes*.)*
