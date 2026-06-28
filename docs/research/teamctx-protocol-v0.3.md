# Certified Context for Autonomous Coding Agents
### Observable Soundness and the Privacy–Coverage Tradeoff in Deterministic Mediation
*Working paper v0.3, second major revision. Role: Distributed Systems & Security research pair. Internal stress-testing document.*

---

## Response to Reviewers (round 2)

Round-2 verdicts moved from unanimous *reject* (v0.1) to *major revision* (with one conditional *strong accept*). v0.3 closes the five remaining valid defects; all are bounded edits, not structural changes.

- **[R2-Gemini] T6 definitional collapse, "relevant P-invisible source" is empty under `rel(v,q)`.** *Conceded; fixed.* We separate **global relevance** `rel_G` (over the unpermissioned graph `G`, permission-independent) from the **rendered** predicate `rel_render` (over `Ĝ_P`). T6 now quantifies over `rel_G`; §6 rendering uses `rel_render`. (§3.6, §5/T6)
- **[R2-Gemini/gpt-oss] §5.6 `False` is unsound for structurally-disconnected witnesses.** *Conceded; fixed.* `False` now requires provable completeness over the **global** dependency set `deps_G(ρ)`; otherwise `Unknown`. Disconnected ⇒ `Unknown`. We also add the previously-missing `witness` and `deps_G` maps so the semantics is evaluable. (§5.6)
- **[R2-all] T3′ "never via free-text" overclaims; `φ` is a parser over untrusted bytes.** *Conceded; downgraded.* T3′ now claims only **feature-mediated selection** (selection depends on body only through `φ`'s typed output); the corollary forbids free-form control/instruction injection, not feature movement. **`φ`-robustness** (resistance to formatting-induced misclassification) is an explicit assumption + limitation, not a theorem. (§3.4, §5/T3′, §8)
- **[R2-all] T5′ name overstates; implicit references unmodeled.** *Conceded.* Renamed **Foreign-Key-Based Observable Soundness**; the implicit-reference ceiling is stated in the theorem, not just limitations. (§5/T5′)
- **[R2-all] T6 is a known template; novelty/leakage unquantified.** *Conceded; strengthened.* We cite the correct prior art (declassification, hyperproperties, polyinstantiation, query-completeness) and add a **quantitative δ-leakage bound** so T6 is a *characterized frontier*, not a tautology. (§5/T6, §9)

We note one reviewer's prior-art citations were inaccurate (Certificate Transparency mis-attributed; PBS is not a privacy result); we rely on the correctly-identified template literature instead.

---

## Abstract

Autonomous coding agents act on the live state of a software team but begin each session blind to it. Best-effort retrieval (RAG, long context, memory) is unverifiable, conflates *current* with *correct* and *absent* with *safe*, and is an injection channel by construction. We model agent context as **deterministic certified mediation under partial observability** and characterize its limits. `teamctx` returns source-backed *context cards* with a **coverage certificate** `κ` reporting observed sources, freshness, and **dangling references** (typed foreign keys leaving the observed, permitted subgraph). Results: (1) **Foreign-Key-Based Observable Soundness**: claims are sound over the observed permitted subgraph and every typed edge leaving it is reported, so omissions are confined to relevance that is *not encoded as a typed reference or policy* (Thm 5′); (2) a **Privacy–Coverage Impossibility with a quantified declassification dial**: no mediator can both hide the existence of artifacts a principal may not see and report every globally-relevant unobserved source; the dial `δ` navigates the frontier with leakage bounds `0 / ≤log₂(N+1) / full` bits (Thm 6); (3) **Feature-Mediated Selection**: card selection depends on source content only through a fixed typed feature map `φ`, so adversarial text can move an artifact between feature classes but cannot inject free-form control or instructions into selection (Thm 3′). We give evaluable 3-valued guarded semantics for "absence," an adversary analysis, and an explicit accounting of assumptions (typed references, single ingestion order, `φ`-robustness, signed/observed metadata). We claim a *protocol plus a domain-specialized tradeoff characterization*, built from standard primitives.

**Contributions.** (i) context as certified mediation under partial observability; (ii) FK-based observable soundness via dangling-reference certificates; (iii) the privacy–coverage impossibility with quantified `δ`; (iv) feature-mediated selection as the precise, provable core of injection-resistant *selection*.

---

## 1. Introduction

A unit of work is a task on a branch; its truth is scattered across forge, tracker, docs, CI. Agents start cold and confidently fill gaps. Widening intake treats context as *recall*; an *acting* agent instead needs **verifiability** (reproduce what it saw), **permission fidelity** (see only what its principal may; don't leak the rest), a **trust boundary** (source text as evidence, not instructions), and **bounded ignorance** (an explicit statement of what was not seen). Capacity does not supply certificates: a model that ingests more cannot *prove* what it was permitted to know or *bound* what it missed. Our thesis: a context system for an acting agent must return what it found **and** a machine-checkable, structurally-bounded statement of what it could not see, and that statement cannot be both existence-private and complete.

---

## 2. Setting, Threat Model, Assumptions

**Entities.** Principal `P`; Agent `A` (untrusted, acts for `P`); Broker `B` (deterministic, read-only, no learned component in the certified path); Sources `Σ` (forge/tracker/docs/CI) exposing artifacts, permission oracle `vis_P`, totally-ordered event logs.

**Trust.** *Trusted:* policy, connector config, deterministic rules + `φ`, permission results. *Semi-trusted:* sources, for their own *state* (existence, timestamps, ACLs), not artifact *content*. *Untrusted (data, never instructions):* all artifact text.

**Assumptions (A1–A5), stated up front; each has a named residual in §8.**
- **A1 (typed references).** Semantically-relevant cross-source relations are encoded as typed foreign keys, or named in `policy_mandated(q)`. *Residual: implicit free-text references.*
- **A2 (ingestion order).** A single logical sequencer totally orders ingested events (or a CRDT fold proven commutative/associative/idempotent, out of scope). *Residual: multi-sequencer determinism.*
- **A3 (metadata integrity).** State metadata in the certified path (`t_obs`, `status`, foreign keys) is broker-observed or source-signed. *Residual: unsigned-metadata forgery.*
- **A4 (`φ`-robustness).** `φ` resists formatting-induced misclassification by adversarial text. *Residual: parser-confusion (not proven; see T3′).*
- **A5 (ACL fidelity).** `vis_P` reflects current source ACLs up to a bounded skew. *Residual: stale permissions.*

**Adversaries.** `Adv₁` malicious author; `Adv₂` curious principal; `Adv₃` eclipse/network; `Adv₄` malicious agent; `Adv₅` compromised source; `Adv₆` honest-but-wrong source.

---

## 3. Formal Model

### 3.1 Events, logs, snapshots
Per-source totally-ordered logs `L_σ` (idempotent by event id); broker ingestion order (A2). Snapshot `S = fold(prefix)`; **digest** `d = H(cut ‖ ruleset_version ‖ policy_version)`. Determinism is relative to `d`. Observation record `obs(σ)=(t_obs(σ), status(σ))`, `status ∈ {ok, stale, unreachable}`.

### 3.2 Artifacts, graph, permissions
`a = (id, type, scope, state, t_*, prov, sensitivity, trust=untrusted, body, refs)`; `refs` are **typed cross-source foreign keys stored in the originating artifact** (A1). Typed graph `G=(V,E)`. Oracle `vis_P : V→{⊤,⊥}`; restriction `S|_P`.

### 3.3 Two relevance predicates (fixing T6 collapse)
- **Global relevance** `rel_G(v,q)` over the *unpermissioned* graph `G`: `v` is within bounded reachability of `seed(q)` in `G` and `policy_admits(v,q)`. Permission-**independent**; used only in impossibility statements (T6). A **source** `σ` is *relevant* if it owns some `v` with `rel_G(v,q)=⊤`.
- **Rendered relevance** `rel_render(v,q) = (v ∈ Ĝ_P(q)) ∧ policy_admits(v,q)`; used to build `C` (§3.5, §6). Note `rel_render ⇒ rel_G` but not conversely (the gap is the relevance ceiling).

### 3.4 Feature extractor `φ` (fixing T3)
`φ` is a fixed deterministic map `(metadata, body, prior_body) → Φ`, `Φ` a finite typed schema (e.g., `field_changed(acceptance_criteria):bool`, `overlap_hunks:int`). Rules are written in a rule language `L_Φ` whose only body-derived inputs are `Φ`-features; `L_Φ` syntactically forbids raw-`body` predicates (checkable by inspection). **`φ` may read untrusted content; A4 (robustness) is assumed, not proven**: adversarial text can move an artifact between `Φ`-classes (parser confusion), which §5/T3′ scopes precisely.

### 3.5 Observed subgraph, dangling refs, certificate, dial
`Ĝ_P(q)` = nodes reachable from `seed(q)` within depth `k` via edges with both endpoints in `S|_P` and observed. **Dangling reference**: a typed foreign key in a visible `u ∈ Ĝ_P(q)` whose target node is unobserved/unreachable; `D(q)` collects these *without traversing the offline target*. `Req(q) = {sources owning Ĝ_P(q) nodes} ∪ policy_mandated(q)`. Certificate `κ(q) = ⟨{(σ,t_obs,status):σ∈Req(q)}, δ(D(q))⟩`. **Declassification dial** over invisible-target dangling refs: `δ=none` (drop; existence-private), `δ=count` (report cardinality only), `δ=identity` (report fully); visible-target dangling refs always reported.

### 3.6 Generator
`g(S,q,P,δ) = ⟨C,κ⟩ = (render ∘ rank ∘ rules_φ ∘ π_P)(S,q) ⊕ κ(q,δ)`, pure in `(d,q,P,δ)`. Cards carry `agent_instruction` (fixed vocabulary) and source bytes only in `quote(meta,payload)`.

---

## 4. Protocol
`CtxRequest{principal_token, repo, branch, base, paths[], symbols[], linked_refs[], session, δ, d?}` → `CtxResponse{cards C, coverage κ=⟨obs, δ(D)⟩, staleness Δ, coverage_ratio cov, snapshot_digest d, sig}`. `coverage` is non-optional (no "all clear"). Deterministic pipeline: impersonate `P` (least privilege) → build `Ĝ_P` → `rules_φ` → quarantine/defang (`quote`, inert URLs, `status_only` bodies) → assemble `⟨C,κ⟩`, dangling refs via `δ`, sign `H(C ‖ κ ‖ H(q) ‖ d)` for replayable audit.

---

## 5. Properties

**T1′ (Determinism, rel. to `d`).** Under A2 and `d` pinning (prefix, ruleset, policy), `g` is identical for equal `(d,q,P,δ)`. *Sketch:* order-deterministic fold + pure pinned stages. ∎ *Residual:* multi-sequencer ⇒ needs CRDT fold.

**T2′ (Value-channel permission noninterference, `δ=none`).** Partition inputs into **Low** = `S|_P` and **High** = `S∖S|_P`. With `δ=none`, `g` is a function of Low only: `S|_P = S′|_P ⟹ g(S,q,P,none)=g(S′,q,P,none)`. *Sketch:* `π_P` first; `Ĝ_P` uses only `S|_P` edges; `δ=none` drops invisible-target refs. ∎ *Scope (in-statement):* termination- and timing-insensitive, value-channel only; cardinality/timing are out of the value model (mitigations §8). For `δ≠none`, holds up to the declassified function of `D` (T6).

**T3′ (Feature-Mediated Selection).** For `S,S′` differing only in untrusted `body` bytes of visible artifacts, if `φ(S)=φ(S′)` then `g(S,·)=g(S′,·)` up to `quote` payloads. *Sketch:* `rules_φ`/`rank` read only metadata + `Φ` via `L_Φ` (no raw-body predicate). ∎ *Corollary (scoped):* `Adv₁` influences selection **only by moving an artifact between `Φ`-classes**, never by injecting free-form control or instructions into the instruction channel. *Honest limits:* (i) under ¬A4, adversarial formatting can spoof a `Φ`-class (parser confusion), a `φ`-robustness problem, not closed here; (ii) `B` types delivery but cannot force `A` to honor `quote` (§8).

**T4′ (No Ex-Nihilo Cards).** Every `c∈C` has a witness that is an artifact in `S|_P` or an observation record in `κ`. *Sketch:* rules fire only on present witnesses. ∎ *Note:* a provenance property (no fabrication), not semantic correctness of the card's claim.

**T5′ (Foreign-Key-Based Observable Soundness).** Under A1: (i) every `c∈C` is sound over `Ĝ_P(q)`; (ii) every **typed foreign key** leaving `Ĝ_P(q)` to an unobserved target appears in `D(q)` (subject to `δ`). Hence omissions are confined to relevance **not encoded as a typed reference and not policy-mandated**. *Sketch:* (i) T4′ over `Ĝ_P`; (ii) `D` read from foreign keys present in `Ĝ_P`. ∎ *Residual (in-statement):* implicit free-text references (¬A1), structurally-disconnected relevant sources, and stale permissions (¬A5) are undetected; this is the relevance ceiling.

**T6 (Privacy–Coverage Impossibility, with quantified dial), headline framing.** Define **Existence-Privacy (EP):** `g` invariant under changes confined to `P`-invisible artifacts. **Coverage-Completeness (CC):** for every *globally-relevant* (`rel_G`) unobserved source `σ`, `κ` reports `σ`'s existence. **If a globally-relevant `P`-invisible source can exist, EP and CC are jointly unsatisfiable.** *Proof:* take `S` with such a `σ` and `S′=S∖{σ}`; `σ` invisible ⇒ `S|_P=S′|_P`; CC ⇒ `κ(S)`≠`κ(S′)` ⇒ EP fails. ∎ *Quantified frontier (the substantive part):* let `N=|invisible-target dangling refs|`. Leakage about invisible existence is `δ=none: 0 bits` (value channel), `δ=count: ≤ log₂(N+1) bits`, `δ=identity: full`. So `δ=none` is the max coverage compatible with EP (= P-relative completeness); `δ` is a *necessary* control on the frontier, not a wart. *Positioning:* this is the noninterference-vs-completeness / declassification tension (Sabelfeld–Myers; Clarkson–Schneider; polyinstantiation; query-completeness) **specialized to agent context**, with the leakage quantification as the modest new content, not a new impossibility.

### 5.6 Guarded semantics (evaluable; fixing `False`)
Let `witness : C → 2^Prop` map each card to the propositions it establishes, and `deps_G : Prop → 2^Σ` the **global** sources whose state can affect `ρ` (over `G`, not `Ĝ_P`). Define `⟦·⟧ : Prop → {True, False, Unknown}`:
- `⟦ρ⟧ = True` if some `c∈C` with `ρ ∈ witness(c)`;
- `⟦ρ⟧ = False` **iff** every `σ ∈ deps_G(ρ)` is present in `κ` with `status=ok` **and** no witness exists (negation established over *complete global coverage*);
- `⟦ρ⟧ = Unknown` otherwise, including whenever any `σ ∈ deps_G(ρ)` is missing from `κ` (e.g., structurally disconnected, stale, or unreachable).
Because the relevance ceiling (T5′) usually prevents proving `deps_G(ρ) ⊆ Req(q)` complete, `False` is rare and `Unknown` is the conservative default, which is the intended honest behavior. The consumer obligation is the typing rule `treat Unknown ≠ False`; `κ` supplies the bits, `deps_G` the dependency set. `B` cannot force `A` to honor it (§8).

---

## 6. Relevance without Learning
Rendering uses `rel_render` (§3.3): decidable, `O(|V|+|E|)` bounded BFS over `Ĝ_P`. Card kinds: `overlapping_change · linked_issue_changed_after_branch · acceptance_criteria_changed · required_checklist_changed · advisory_affects_touched_dependency · related_branch_ci_failure · doc_superseded · source_unavailable`. An **untrusted client-side hint layer** may reorder/de-emphasize *already-certified* cards (any method, incl. an LLM or a reference-extractor for implicit links) but **cannot add to/remove from** `C`, so it cannot perturb T1′–T6, and any implicit-reference recovery it performs is explicitly untrusted.

---

## 7. Stress Tests
| Adversary | Guarantee | Residual |
|---|---|---|
| `Adv₁` author | T3′: selection only via `Φ`-class; no free-form control injection; content delivered defanged | `φ`-class spoofing under ¬A4; true-but-misleading artifacts surfaced faithfully |
| `Adv₂` curious principal | T2′ (`δ=none`): output = f(Low); T6 quantifies any `δ`-leak | timing/cardinality side channels (§8) |
| `Adv₃` eclipse | typed dangling refs + `unreachable` status make missing *referenced* targets visible; `Δ` grows | implicit/disconnected refs (¬A1) |
| `Adv₄` agent | read-only + T2′ bound to `P`'s perms; signed audit | cannot police `A`'s use of output |
| `Adv₅` source | fidelity + provenance; signing per A3 | unsigned-metadata forgery |
| `Adv₆` honest-but-wrong | deterministic conflict/staleness/`doc_superseded` signals surface garbage as garbage | cannot adjudicate truth |

Pattern: silent failures become visible signals in `C`/`κ`, **except** the named residuals (¬A1 implicit refs, ¬A3 unsigned forgery, ¬A4 spoofing, ¬A5 skew, disconnection), which we surface rather than hide.

---

## 8. Limitations
Each maps to an assumption: **A1** implicit references (large in practice; recoverable only via untrusted parsing → §6 hint layer); **A2** multi-sequencer determinism; **A3** unsigned metadata; **A4** `φ` parser-confusion (T3′ residual); **A5** ACL skew (a `permission-freshness` certificate is open work). Plus: **fidelity ≠ truth** (T4′); **agent-cooperation** (B types the boundary, cannot enforce on A; an enforcing consumer is a different, invariant-breaking product, excluded); **bounded not real-time freshness** (CAP-style; `Δ` quantifies); **side channels** (timing/cardinality outside the value model; padding/constant-time walk reduce, not eliminate).

---

## 9. Related Work
**Reference monitors / complete mediation:** Anderson 1972; Saltzer–Schroeder 1975. **IFC, noninterference, declassification, hyperproperties:** Denning 1976; Goguen–Meseguer 1982; Sabelfeld–Myers 2003; Clarkson–Schneider 2010, T2′ is value-channel access-control-grade, not full IFC; T6 is an instance of the noninterference-vs-completeness/declassification tension. **Inference control / completeness:** Jajodia–Sandhu polyinstantiation; Motro 1989 (query completeness), closest precedents for EP↔CC. **Provenance:** W3C PROV; PASS (Muniswamy-Reddy et al. 2006), `κ`/`D` is a missing-provenance manifest. **Authenticated structures / transparency logs:** Merkle; Certificate Transparency (Laurie–Langley–Kasper, RFC 6962), basis for signed replay. **Consistency/staleness:** Lamport 1978; CRDTs (Shapiro et al. 2011); PBS (Bailis et al. 2012). **LLM injection:** Greshake et al. 2023; the Dual-LLM pattern (complementary: hardens the *consumer*; we harden *selection/delivery*). **Best-effort retrieval:** RAG (Lewis et al. 2020); MCP. **Positioning:** synthesis + FK-based observable soundness + a δ-quantified EP↔CC frontier + feature-mediated selection; the cryptographic/consistency primitives are standard.

---

## 10. Discussion
Honest contribution: **a context mediator for an acting agent cannot be both existence-private and coverage-complete; the achievable optimum is foreign-key-based observable soundness plus a quantified declassification frontier.** Less than certified omniscience, more than best-effort recall: falsifiable, replayable, and explicit about a boundary recall-based systems cannot name. The sharpest open problem is tightening the `δ`-leakage analysis (per-source, information-theoretic) and measuring the relevance ceiling empirically (what fraction of behavior-changing context flows through typed references vs. implicit text, A1's practical validity). Other open work: permission-freshness certificates; a verifiable `L_Φ` with a mechanized no-raw-body check; a cooperating-consumer profile; mechanized proofs.

---

## 11. Conclusion
`teamctx` v0.3 frames agent context as deterministic mediation under partial observability: source-backed cards plus a coverage certificate sound over what was observed and explicit about what was not, and proves no such mediator can be both private about the invisible and complete about the relevant, with a quantified dial over the residual. It promises not truth or omniscience but something checkable: within the region it can see, it will not lie to your agent by omission, and it tells you, by construction, where that region ends.
