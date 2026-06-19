# teamctx — Architecture Decision Record (v0)

*Status: **decided spine**, with named-open items (§9). This is the model that
underlies the vision artifacts ([day-in-the-life](day-in-the-life.md),
[personas](personas.md)) and grounds in the formal protocol
([v0.3](../../research/teamctx-protocol-v0.3.md) +
[v0.4](../../research/teamctx-protocol-v0.4.md)). Where a decision here extends the
protocol, it is flagged as needing a formal-model update. Bar: **claims never
outrun proof** — §10 separates proven / decided / open.*

---

## 0. What teamctx is

A **deterministic, no-LLM, read-only context broker** for AI coding agents. At the
start of a unit of work (a new branch, a resumed session), any connected agent —
Claude Code, Codex, Gemini CLI, Cursor, opencode — asks the broker for context. It
returns compact, typed, permission-scoped **context cards** ("an open PR already
touches this symbol", "the linked acceptance criteria changed after your branch
point", "this doc was superseded") plus a **coverage certificate** that honestly
reports what was observed, what is stale, and what is unknown.

One design decision — **no LLM in the *content path*** — yields the whole value.
**Positioning is specified in [positioning.md](positioning.md)** (resolves open-item #10,
2026-06-19, and supersedes the earlier "lead with can't-track" order that sat here). Short
form: the **marquee** is the *category* — **timely, ambient team context** (humans and
their agents on the same live picture of the work and its standards) — and the properties
below are its **credibility engine**: the *because* that makes the category claim
trustworthy and differentiated. They moved from *banner* to *proof*; they are exactly as
load-bearing as before.

- **Can't track — by construction, not policy.** Structural non-retention, no people-graph,
  no read receipts (D1, §6). Amplifies *artifacts*, never *behavior*.
- **Can't be hijacked.** Source text is untrusted evidence, never instruction; selection is
  feature-mediated (§7). Hardens its *selection pipe* — end-to-end safety needs a
  cooperating agent (§8); we do not claim "incapable of harm."
- **Honest coverage + preserved velocity.** Absence ≠ all-clear; it reports what it didn't
  check instead of guessing (§5). The same no-LLM/read-only/retains-nothing decision makes
  it can't-track, can't-fabricate, **and** honest — the proof the safety is structural.
- **The reference, not the rival.** Because facts arrive **verbatim and source-backed**,
  teamctx is the deterministic ground an agent stands on and checks itself against —
  **complementary** to the LLM (the product exists *because* of agents), scoped to *what is
  currently true in the record* (not judgment; not "is the record correct").
- **Cross-agent portability** — context is data, so the consumer is swappable.

**Safety-of-teamctx is table stakes; token/latency is an objection-handler** — neither is
the promise. To *"won't a layer talking to my agents every turn burn tokens and slow
everything down?"* — no: net-cheaper than the status quo it replaces, at ~8ms p95
(warm-daemon, §9), with **measured, bounded** receipts — never a total-cost meter.

---

## 1. Decision: Two packages, one product — the evidence/authority seam

**Decision.** Ship a **stateless broker** as the base package, and a **durable
memory layer** as a *separate, optional* package. One product, two artifacts.

**Why the seam sits exactly here.** The broker and the durable layer make
*opposite* promises about state, and those promises collide inside one artifact:

| Promise | Requires | Lives in |
|---|---|---|
| "it can't track — it can't" | **non-retention** | stateless broker |
| "agents start knowing what the team decided" | **retention** | durable memory |

This is the **evidence vs. authority** split. The broker serves **evidence**
(ephemeral facts that are a pure function of current source state). The durable
layer holds **authority** (declared, reviewed, durable "what should be true").
These are different record types with different lifecycles; conflating them makes a
defensible, auditable decision impossible. Read-only safety against *source writes*
is delivered by credential scope (available to both); the property only a separate
artifact can give is **non-retention provable by absence** — the durable code is
not in the lockfile/SBOM, so "this deployment cannot retain" is an auditable fact,
not a config flag.

**The capability ladder (configurations, not editions).** Capability-absence is
enforceable at four+ independent, stackable layers. Solo needs none; a regulated
enterprise stacks all of them:

1. **credential** — read-only OAuth scopes (can't write to sources).
2. **egress** — network-egress policy + a **trusted-connector allowlist**. *This is
   the load-bearing rung:* any plug-in connector with network access is a potential
   exfiltration/retention path. SBOM-absence proves the absence of the *first-party
   durable store*, not the absence of retention/exfil capability in general.
3. **dependency** — durable package absent from the lockfile.
4. **package / process** — durable code not on disk; broker in its own process with
   only read credentials.

**Coupling rule.** Strictly one-way: the **broker is ignorant of the durable
layer**; the durable layer depends on the broker's interfaces, never the reverse
(enforced by an import guard). The durable layer registers as **just another read
source** through the same connector interface as GitHub/Jira — so the broker stays
stateless *even when memory is present*; only the durable package retains. Deleting
the durable layer changes **zero lines** of broker code.

**Collapse-prevention.** The broker must be fully useful with the durable layer
absent. CI runs the full broker suite with it uninstalled. The moment the README
says "for team knowledge, also install …" as a *required* step, the seam has
collapsed into one product pretending to be two.

**Implementation.** The broker is an **extraction** from the shared pure
foundation (core + read connectors + transports), not a rewrite — it is the
assembly that omits the durable/write code.

---

## 2. Decision: Product *and* protocol — standardize the edges, own the engine

**Decision.** Publish the **contract** — context-card schema, coverage-certificate
semantics, connector interface, transport — as a versioned specification. Keep the
**extraction engine a single, canonical, reproducible artifact.** Do **not** invite
third-party *engine* reimplementations in v1.

**Rationale.** Determinism is the value proposition, and determinism dies under
semantic drift: two "compliant" engines parsing the same PR differently produce a
1% context difference, which for an agent is a 100% behavior difference. The
contract is what agents/IDEs/connector-authors integrate against and what a
security team audits; the canonical engine is what keeps the guarantee real.

---

## 3. Decision: Cross-agent transport + a human plane that never routes through the LLM

**Decision.** Hybrid transport: **file + CLI + MCP**.

- **File adapter** — written at work-start (e.g. via a session/checkout hook), human-
  readable, any client that can read a file consumes the same context with no
  integration. This is the cross-agent foundation; it is *stronger* than an IDE
  plugin because it is per-everything, not per-IDE.
- **CLI** — the universal pull/inspect path.
- **MCP** — the interactive machine path.

**Two planes, one core.** The **machine plane** (MCP → agent) delivers the *value*;
the **human plane** delivers the *trust*. The human plane (the file, the CLI,
optionally an IDE panel) renders the **same certified cards directly to the human**,
**never relying on the LLM to relay them**. Every human surface is a *deterministic
renderer* of the certified cards — never an in-editor LLM assistant. The human plane
**prints, never blocks**; enforcement is the opt-in, availability-harm-owned config
of §6, not a default.

---

## 4. Decision: The card model — Route / Stamp / Envelope

Every candidate claim produces **two independent outputs**, computed by different
machinery, plus a per-request envelope:

- **ROUTE** — *should it surface, how loud, in which trust tier?* Owns **noise**.
  **Tunable.**
- **STAMP** — *how is it honestly framed?* Owns **honesty**. **Reported fact, never
  tunable.**
- **ENVELOPE** — the coverage certificate; owns **absence**. Reported fact.

**Two failure families, and trust is multiplicative.** There are exactly two ways
to lose trust: **cry wolf** (Route too loose) and **lie** (Stamp dishonest —
stale-shown-as-fresh, conflict-shown-as-resolved, fidelity-shown-as-truth). Trust
composes *multiplicatively* across cards: one phantom or one mis-stamp poisons the
whole surface (the dev stops reading all of it). So the bar is: conservative on
**every axis simultaneously, every time.**

**The composition algebra.** Each signal has exactly one algebraic role, and the
intersections are then *computed*, not enumerated:

| Signal | Role | Layer | Tunable? |
|---|---|---|---|
| on-target (any structural edge to your work) | hard gate (veto→0) | Route | threshold |
| phantom-check (file overlap, no symbol overlap) | hard gate (veto→0) | Route | threshold |
| novelty (already seen since branch point) | hard gate (veto→0) | Route | window |
| relevance-strength (how direct/many edges) | additive flavor | Route | weight |
| severity (§5) | additive flavor + interaction | Route | weights |
| freshness → priority discount | multiplicative precondition | Route | tolerance/steepness |
| severity × freshness | interaction (sev widens stale tolerance) | Route | strength |
| severity × relevance | interaction (high-sev fires only if relevant) | Route | strength |
| volume budget | global gate (rank-and-cap) | Route | cap |
| target-confidence (structural vs semantic) | categorical router → tier | Route | ❌ fixed |
| freshness → label, authority-state (§6) | categorical stamp | Stamp | ❌ fact |
| fidelity (is it true?) | standing caveat | Stamp | ❌ out of scope |
| coverage | envelope | Envelope | ❌ fact |

```
ROUTE:
  priority = [ on_target ∧ ¬phantom ∧ novel ]                 # hard gates → drop
           × clarityFactor(age, tol(severity), steepness)     # multiplicative precondition
           × sigmoid( w_rel·relevance + w_sev·severity
                      + w_int·(severity·relevance) )          # flavors + interaction
  then RANK survivors → CAP at volume_budget
       → ROUTE by target_confidence into { certified, hint }

  clarityFactor(load, tol, steep) = 1 / (1 + (load/tol)^steep)   # 1 fresh, 0.5 at tol, →0
```

**Trust tiers are a firewall.** **certified** = deterministic, provable,
replayable (structural / declared). **hint** = best-effort semantic guess, starkly
labeled, never certified. The boundary is a *trust firewall*: the certified surface
keeps its value (rely on every item without checking) only if nothing uncertain
ever leaks in. The hint tier is also the **pressure valve** for the Route's
precision/recall bind — a borderline card is *demoted to a labeled hint*, never
silently dropped (the "you didn't warn me" betrayal) and never faked as certified.

**Tune the gate, never the truth.** Every tunable knob lives in Route (the noise
floor, weights, tolerances — Raj's `.teamctx` policy, dragged in a dry-run/preview
**Lab**). Every fact lives in Stamp/Envelope. You can tune how *loud* a stale card
is; you can never tune the "2h old" label *off*. The two layers are physically
separate and cannot bleed.

---

## 5. Decision: Severity

**Severity = a deterministic estimate of the cost of *not knowing this at
work-start*.** Computed from structure, once, server-side — never learned, never an
LLM judgment. Three deterministic drivers:

```
severity = clamp01( kind_base × (1 + α · magnitude_norm) × scope_mult )
```

- **kind_base** — intrinsic stakes of the event class (fixed typed table; defaults
  below).
- **magnitude_norm ∈ [0,1]** — blast radius: dependency/link fan-out of the changed
  subject. A structural graph fact.
- **scope_mult ≥ 1** — declared-sensitive domains (`payments/`, `auth/`) lifted via
  `.teamctx`.

**Default kind-base table (starting positions, tuned per shop):**

| Card kind | base |
|---|---|
| authority-conflict (your sources contradict) | 0.85 |
| active collision (same symbol, open PR) | 0.80 |
| missed required gate (compliance checklist) | 0.80 |
| superseded spec / criteria changed | 0.60 |
| dependency / contract change | 0.60 |
| non-authoritative dissent | 0.40 |
| related FYI (different area) | 0.15 |

**Magnitude ≠ relevance.** Relevance = how directly it touches *my* work (edges
from me → subject). Magnitude = how much it matters *in general* (subject's global
fan-out). High-magnitude + low-relevance → quiet/hint; the `severity×relevance`
interaction is what asks "high-stakes, but is it *mine* right now?"

**Authority needs no special case:** `conflicted` and `dissent` are simply
high-`kind_base` rows. Authority feeds severity by being a high-stakes *kind*.

**Tunable vs. fixed.** Tunable (Route, risk appetite): kind_base values, `α`, scope
multipliers. Fixed (fact): magnitude (computed from the graph — a 30-dependent
symbol can't be tuned small); and severity can never tune a stale/conflict *label*
off (that's Stamp).

**Keeps structure.** Severity collapses to a scalar for ranking but carries its
decomposition into the card `why` and the certificate — *"HIGH = collision × 30
dependents × payments-scope"* — replayable and explainable.

**Honest edge.** When fan-out is coverage-partial, magnitude is a **lower bound**
and the card is stamped `partial` — we under-claim, never fake precision.

---

## 6. Decision: Authority as a first-class record  *(extends the protocol)*

**Decision.** Add **authority** — a *declared* mapping (scope → source → priority),
applied deterministically, surfaced **informationally, never enforced**. States:

- `resolved` — one declared authority applies → "authoritative value is X per «decl»".
- `missing` — **the honest default.** No declaration → the broker **refuses to
  pick**. It surfaces only the *structural* fact that both linked artifacts
  **changed / are relevant** ("they may now disagree — check"), which needs no value
  extraction. It does **not** certify that they disagree *on a value* — see the
  measured result below; an undeclared value-disagreement is at most an L hint.
- `conflicted` — multiple declared authorities disagree → one **conflict card**,
  both shown, no winner asserted, human resolution recommended.
- `temporary` — scoped + expiring override.

**Suppress vs. demote** (resolved by "does it add information?"): a non-authoritative
source that **agrees** with the authority is redundant → **suppress**; one that
**disagrees** is dissent = signal → **demote, never suppress** (suppressing dissent
is a Stamp-honesty failure).

**Two layers.** Authority *behavior* (missing-default, refuse-to-pick,
surface-conflict) is **core** and small. Authority *declarations* are
**additive-with-investment**: lightweight in `.teamctx` (no durable layer needed) →
durable/governed in the memory layer. This is what makes Priya's decisions
propagate (declared authoritative) and carries the staff/principal "global mandate"
(a broad-scope declaration) — neither of which structural relevance handled.

*Formal-model impact:* authority is a new declared input and a new coverage state;
soundness claims must be stated **relative to declared authority**, and the
guarded-semantics `Unknown` splits into *unobserved* / *no-authority-declared* /
*authority-conflict*. Folds into a protocol v0.5.

---

## 7. Decision: Relevance is structural-by-design; learned signals advise, never certify

**Decision.** The certified core is **structural** (explicit graph edges: file/
symbol overlap, linked-artifact changed-since-branch, required gates, dependency
edges, superseded versions). It does **not** learn and does **not** track — that is
the moat, not a limitation.

**The S / D / L tiers.**

- **S — structural** (certified, ~minority of all high-value events but the
  *certifiable, highest-confidence, costliest-to-miss, agent-can't-self-derive*
  slice).
- **D — declared** (authority/policy; certified once human-reviewed — §6).
- **L — learned/semantic** (untrusted hint tier; fuzzy guesses, clearly labeled).

**Rock-solid = honest coverage, not total coverage.** Value isn't "cover
everything"; it's *never confuse "I can't see it" with "it's fine."* The size of L
doesn't make the broker a grep tool, *provided* the certificate marks the unknowns
and L stays in the hint tier. The **L→D flywheel**: the broker's honest "Unknown /
didn't observe X" is the *incentive* to write tribal knowledge into a linked or
declared artifact, converting fuzzy L into trustworthy D over time. No learned
feedback loop lives in the broker; deterministically-mineable signals (e.g.
co-change) may move into S, declarations into D, fuzzy guesses stay L.

**Phantom filter (diagnostic vectors).** Multiple deterministic typed judges per
candidate; the *pattern* classifies the card. file-overlap=yes ∧ symbol-overlap=no
→ **phantom collision** → suppress. doc "changed" but diff is whitespace/typo →
**phantom doc-change** → suppress. This is the deterministic, no-ML cure for alert
fatigue, and it gates §6's undeclared-disagreement detection.

**Coverage taxonomy.** The certificate distinguishes `fresh / stale(age) / partial
/ unreachable / missing / unsupported`, plus `unverified` ("the world changed; can't
confirm your work accounts for it"). Each implies a *different agent action* — the
point of not flattening.

---

## 8. Honesty invariants (the hard lines)

- **Read-only.** No write path to sources in the broker package.
- **Can't-track by non-retention** (structural, not policy): the broker retains no
  durable trusted state. Ephemeral, freshness-stamped, force-refreshable caches are
  permitted and required for latency; they are not "tracking".
- **Absence ≠ clearance.** Enforced by the envelope; the consumer obligation is
  `Unknown ≠ False`.
- **Fidelity ≠ truth.** The broker reports faithfully what a source says; it does
  not validate that the source is correct. Standing caveat, never per-card noise.
- **Deterministic + replayable.** Same inputs → same outputs; a signed coverage
  certificate + snapshot digest re-derives any past output.
- **Tune the gate, never the truth.** Route is tunable; Stamp/Envelope are reported
  fact.
- **No people-graph.** Artifact-centric; no read receipts, presence, sentiment, or
  productivity signals — ever.
- **Bounded-harm, honestly scoped.** The broker hardens its selection pipe
  (injection-resistant *selection*); end-to-end safety still needs a cooperating
  consumer. We do not claim "incapable of harm".

---

## 9. Performance & the I/O tax

A naive "verify every source on every request, no cache" design adds seconds per
request (modeled: ~4s p95 over four cloud sources). The broker is a **warm daemon**
with freshness-stamped per-source caches refreshed by a background loop:
per-request latency is a cache read (modeled ~8ms p95); the cost moves to
**staleness**, which the certificate reports honestly (bounded by the refresh
interval). "Stateless" therefore means *no durable trusted state*, not *no cache*.

---

## 10. Status: proven / decided / open

**Proven (protocol v0.3 + v0.4):** observable soundness; foreign-key soundness
(T5′); no-fabrication (T4′); existence-privacy with the δ dial (T2′/T6); guarded
semantics + sound consumer rule (§5.6); feature-mediated selection (T3′).

**Decided (this doc):** the two-package evidence/authority seam + capability ladder
(D1); product-and-protocol / own-the-engine (D2); hybrid transport + human plane
(D3); Route/Stamp/Envelope + the composition algebra + trust-tier firewall +
tune-the-gate-never-the-truth (D4); severity (D5); authority as a first-class record
(D6); structural-by-design relevance + S/D/L + honest-coverage + phantom filter +
coverage taxonomy (D7).

**Open (named, not hidden):**
1. **Phantom / φ-robustness (A4).** The symbol-overlap judge is doing gate-work; if
   it is weak, phantoms leak or real collisions get vetoed. Our shakiest assumption.
2. ~~Undeclared-disagreement rate~~ — **RESOLVED 2026-06-18**
   ([result](../../research/reviews/arch-panel-2026-06-18/disagreement-experiment-result.md)).
   Two deterministic detectors hit **precision 0.44** on a 48-item adversarial corpus
   (FPs concentrated in representation + superseded-section; freetext recall 0).
   Decision: **undeclared value-disagreement stays an L hint.** The broker certifies
   only "both changed / both relevant" (no extraction) and declared-authority
   comparison on a *typed* field. Revisit only by beating ~0.9 precision on this kind
   of adversarial corpus.
3. **Severity calibration** — the default kind-base table and `α` are guesses;
   needs a real-fixture pass.
4. **Formal-model extension (v0.5)** — fold in authority (D6) and diagnostic-vector
   classification (T3′→T3″).

---

*Next: (2) the `rit` disagreement-rate experiment, (3) severity calibration, then
protocol v0.5 to formalize D6.*
