# Certified Context for Autonomous Coding Agents
### Observable Soundness and the Privacy–Coverage Tradeoff in Deterministic Mediation
*Working paper v0.2 — major revision responding to four referee reports on v0.1. Role: Distributed Systems & Security research pair. Still an internal stress-testing document; claims are stated to be attacked.*

---

## Response to Reviewers (changelog)

We thank the four referees. The reports converged on five valid defects; v0.2 addresses each, and in doing so the contribution sharpened from a slogan into a theorem.

- **[R-all] "Theorem 5 is circular / the reachability paradox."** *Conceded; fixed.* `Req(q)` no longer depends on traversing offline sources. We introduce **dangling references** in the *observed permissioned subgraph* `Ĝ_P` and downgrade the claim from global to **local observable soundness** (Thm 5′). The honest residual — *truly disconnected* relevant sources — is stated as a limitation.
- **[R-all] "Dissolves → relocates the absence-as-clearance fallacy."** *Conceded.* We drop "dissolve." `κ` makes the ignorance boundary *explicit and machine-checkable*; correct consumption is an obligation we formalize (3-valued guarded semantics, §5.6) but cannot enforce on the agent.
- **[R-DeepSeek/R-Gemini] "Fixing the κ-leak (T2) reintroduces silent omission (T5)."** *This tension is now the headline.* We prove it is **fundamental** (Thm 6: Privacy–Coverage Impossibility) and expose a **declassification dial** `δ`.
- **[R-all] "T1 hand-waves out-of-order events; T3's payload-irrelevance is unproven; T4 misnamed."** *Fixed:* explicit event total-order assumption (T1′); a fixed typed **feature extractor `φ`** with a **payload-invariance** theorem (T3′); T4 renamed *No Ex-Nihilo Cards* with observation-records as admissible witnesses.
- **[R-all] "Novelty oversold."** *Conceded.* We reposition as a *synthesis + two results* (observable soundness under partial observability; the privacy–coverage tradeoff) and cite the raised prior art (PBS, Certificate Transparency, W3C PROV/PASS, query-completeness, authenticated data structures, Dual-LLM).

---

## Abstract

Autonomous coding agents act on the live state of a software team but begin each session blind to it. The prevailing remedy — best-effort retrieval (RAG, long context, agent memory) — is unverifiable, conflates *current* with *correct* and *absent* with *safe*, and is an injection channel by construction. We model agent context as **deterministic certified mediation** and study its limits. We define `teamctx`, a read-only protocol that returns source-backed *context cards* with a **coverage certificate** `κ` reporting observed sources, their freshness, and **dangling references** to unobserved ones. Our results: (1) **Observable Soundness** — every emitted claim is sound over the observed, permitted subgraph, and every cross-source edge leaving it is reported, so the *only* omissions are structurally undetectable ones (Thm 5′); (2) a **Privacy–Coverage Impossibility** — no mediator can simultaneously hide the existence of artifacts a principal may not see (existence-privacy) and report every relevant-but-unobserved source (coverage-completeness) whenever a relevant invisible source exists (Thm 6), which we navigate with a declassification dial `δ`; (3) **Payload-Invariant Selection** — card selection depends on source content only through a fixed typed feature extractor `φ`, so an adversary authoring artifacts can influence *which* cards appear only via honest structural signals, never via free-text content (Thm 3′). We give 3-valued guarded semantics for "absence," an adversary-by-adversary analysis, and an honest accounting of what determinism buys (reproducible audit, value-channel noninterference) and what it does not (truth; end-to-end agent safety).

**Contributions.** (i) A formal model of context as certified mediation under *partial observability*; (ii) **Observable Soundness** via dangling-reference certificates; (iii) the **Privacy–Coverage Impossibility** and its declassification dial; (iv) **Payload-Invariant Selection** as the precise, provable core of "injection-resistant selection." We claim a *protocol and a tradeoff result*, not a breakthrough; the cryptographic and consistency primitives are standard.

---

## 1. Introduction

A unit of work is a task on a branch; its truth is scattered across forge, tracker, docs, and CI. Agents discover it never — they start cold and confidently fill gaps. The dominant fix widens intake (bigger windows, retrieval, memory), treating context as *recall*. Recall cannot provide what an *acting* agent needs: a reviewer must reproduce what the agent saw (verifiability); the agent must see only what its principal may (permission fidelity); adversarial source text must arrive as evidence, never instructions (trust boundary); and the system must be honest about what it did **not** observe (bounded ignorance).

The central lesson of v0.1's review is that the last two requirements are in tension with the second, and that honesty about ignorance is *limited by structure*, not free. v0.2 makes both precise. Our thesis: **a context system for an acting agent must return not only what it found, but a machine-checkable, structurally-bounded statement of what it could not see — and that statement cannot be both complete and existence-private.**

Capacity (10M-token windows) does not change this: a model that ingests more cannot *prove* what it was permitted to know, *certify* what it failed to fetch, or *bound* its own ignorance. Capacity does not produce certificates.

---

## 2. Setting and Threat Model

**Entities.** Principal `P` (human); Agent `A` (untrusted, acts for `P`); Broker `B` (`teamctx`: deterministic, read-only, no learned components in the certified path); Sources `Σ` (forge, tracker, docs, CI), each exposing artifacts, a permission oracle `vis_P`, and a totally-ordered event log (§3.1).

**Trust.** *Trusted:* policy, connector config, the deterministic rules + `φ`, permission results. *Semi-trusted:* sources, for their own *state* (existence, timestamps, ACLs) but **not** the *content* of artifacts authored in them. *Untrusted (data, never instructions):* all artifact text.

**Metadata integrity (new assumption).** State metadata used in the certified path (`t_obs`, `status`, edge foreign-keys) is either (a) broker-observed, or (b) source-signed where the source supports it. Adversarial control of *content* is assumed; adversarial forgery of *signed* state metadata is not (an honest residual where signing is unavailable, §8).

**Adversaries.** `Adv₁` malicious source author (content injection / misleading artifacts); `Adv₂` curious principal (infer invisible artifacts); `Adv₃` network/eclipse (delay/drop events); `Adv₄` malicious agent; `Adv₅` compromised source (lies about state); `Adv₆` honest-but-wrong source (stale truth).

---

## 3. Formal Model

### 3.1 Events, logs, snapshots (fixing T1)

Each source `σ` emits a **totally-ordered event log** `L_σ` (per-source sequence numbers; duplicates idempotent by event id). `B` assigns a **broker ingestion order** to incoming events (a single logical sequencer at the trusted monitor). A **snapshot** `S = fold(prefix)` over the ingested events up to a pinned cut. The **snapshot digest** `d = H(cut ‖ ruleset_version ‖ policy_version)` pins the event prefix *and* the effective rules/policy. All determinism claims are **relative to `d`**, not wall-clock. (Concurrency across sources is resolved by ingestion order; if a deployment instead uses CRDT merge, the fold must be proven commutative/associative/idempotent — out of scope here.)

For each `σ`, an **observation record** `obs(σ) = (t_obs(σ), status(σ))`, `status ∈ {ok, stale, unreachable}`.

### 3.2 Artifacts, graph, permissions

Artifact `a = (id, type, scope, state, t_created, t_updated, prov, sensitivity, trust=untrusted, body, refs)`, where `refs` are **explicit cross-source foreign keys** stored *in the originating artifact* (this is what makes dangling detection possible; §3.4). Typed graph `G=(V,E)` with deterministic relations (`pr —modifies→ path`, `branch —references→ issue`, `issue —links→ doc`, `pr —overlaps→ pr`, …). Permission oracle `vis_P : V → {⊤,⊥}`; restriction `S|_P = {a : vis_P(a)=⊤}`.

### 3.3 Typed feature extractor `φ` (fixing T3)

`φ` is a **fixed, broker-defined, deterministic** map from `(metadata, body, prior_observed_body)` to a value in a **finite typed feature schema `Φ`** — e.g. `field_changed(acceptance_criteria): bool`, `change_kind ∈ {none,added,removed,modified}`, `overlap_hunks: int`. `φ` *may read content* but emits only schema-typed features. Rules and ranking branch **only** on metadata and `φ`-features, never on raw `body` bytes, and `Φ` admits **no free-text predicate** (no "if body contains string s"). This is a static discipline checkable by inspecting the rule set against `Φ`.

### 3.4 Observed permissioned subgraph, dangling references (fixing T5)

Given request `q` with seed `seed(q)`, the **observed permissioned subgraph** is
`Ĝ_P(q) = { v reachable from seed(q) within depth k using edges whose endpoints are in S|_P and observed }`.
A **dangling reference** is a foreign key `r ∈ refs(u)` for some visible `u ∈ Ĝ_P(q)` whose **target** is unobserved or unreachable (its node is not materialized). Let `D(q)` be the set of dangling references, each carrying `(edge_type, target_source, target_ref, reason ∈ {stale,unreachable,unobserved})`.

Crucially, `D(q)` is computed **without traversing the offline source** — it is read off the foreign keys *present in the observed subgraph*. This breaks v0.1's circularity.

### 3.5 Coverage certificate, declassification dial

`Req(q) = {sources owning nodes in Ĝ_P(q)} ∪ policy_mandated(q)`.
`κ(q) = ⟨ {(σ, t_obs(σ), status(σ)) : σ ∈ Req(q)}, δ(D(q)) ⟩`,
where `δ` is the **declassification dial** applied to dangling refs whose targets are not `P`-visible:
- `δ = none`: drop invisible-target dangling refs (full existence-privacy; coverage is *P-relative*).
- `δ = count`: report only `|invisible-target dangling refs|` (leaks cardinality, not identity).
- `δ = identity`: report them in full (full coverage; existence-privacy sacrificed).
Visible-target dangling refs are always reported. `Δ(q)` (staleness) and `cov(q)` (fraction `ok`) are computed over `Req(q)`.

### 3.6 Card generator

`g(S,q,P,δ) = ⟨C, κ⟩ = (render ∘ rank ∘ rules_φ ∘ π_P)(S,q) ⊕ κ(q,δ)`, a **pure** function of `(d, q, P, δ)`. `rules_φ` branches only on metadata + `Φ`. Cards carry `agent_instruction ∈ {evidence_only, verify_before_relying, apply_when_in_scope}` (fixed vocabulary) and source bytes only inside `quote(meta, payload)`.

---

## 4. The Protocol

```
A → B : CtxRequest { principal_token, repo, branch, base, paths[], symbols[],
                     linked_refs[], session, declass_policy δ, d? }
B → A : CtxResponse { cards: C, coverage: κ = ⟨observations, δ(D)⟩,
                      staleness: Δ, coverage_ratio: cov, snapshot_digest: d, sig }
```
`coverage` is non-optional; there is no "all clear" message. Pipeline (all deterministic): identity resolution (impersonate `P`, least privilege) → build `Ĝ_P(q)` → `rules_φ` over `Ĝ_P(q)` → quarantine/defang (`quote`, inert URLs, `status_only` bodies) → assemble `⟨C,κ⟩`, dangling refs via `δ`, sign `H(C ‖ κ ‖ H(q) ‖ d)` for replayable audit.

---

## 5. Properties

> Proof *sketches*, again stated to be attacked. Each is now **conditional on explicit assumptions**.

**T1′ (Determinism, relative to `d`).** *Assume* per-source totally-ordered logs + broker ingestion order + `d` pins (prefix, ruleset, policy). Then `g(S,q,P,δ)` is identical for equal `(d,q,P,δ)`.
*Sketch.* `S=fold(prefix(d))` is order-deterministic by the ingestion sequencer; `rules_φ, rank, render, π_P` are pure and pinned by `d`. No ambient clock/randomness in the certified path. ∎ *Residual:* if ingestion order is not single-sequenced, determinism requires a CRDT fold (not proven here).

**T2′ (Value-channel permission noninterference, `δ=none`).** With `δ=none`, if `S|_P = S′|_P` then `g(S,q,P,none) = g(S′,q,P,none)`.
*Sketch.* `π_P` is first; `Ĝ_P` uses only `S|_P` edges; `D` under `δ=none` drops invisible-target refs; thus output depends only on `S|_P`. ∎ *Scope (conceded):* this is **termination- and timing-insensitive, value-channel** noninterference — i.e., access-control-grade on the value channel, *not* full IFC. Timing/cardinality side channels are out of model; mitigations (padding `κ`, constant-time `Ĝ_P` walk) in §8. For `δ≠none`, T2′ holds only up to the declassified function of `D` (this is the point of Thm 6).

**T3′ (Payload-Invariant Selection).** For snapshots `S,S′` differing only in untrusted `body` bytes of visible artifacts, *if* `φ(S)=φ(S′)` then `g(S,·)=g(S′,·)` up to `quote` payloads.
*Sketch.* `rules_φ`/`rank` read only metadata and `Φ`; `Φ` has no free-text predicate; so equal `φ`-features ⟹ equal selection. ∎ *Corollary (Selection-Integrity):* `Adv₁` can change *which* cards appear only by changing a `φ`-feature — a genuine structural signal (e.g., the acceptance-criteria field truly changed) — never by embedding keywords or instructions. This is the precise, provable sense of "injection-resistant selection." *Honest scope:* end-to-end agent safety still requires the consumer to honor `quote` typing (§8.2); `B` removes *selection* from the injectable surface and types the *delivery*, but does not police `A`.

**T4′ (No Ex-Nihilo Cards).** Every card `c∈C` has a **witness** that is either an artifact in `S|_P` or an observation record in `κ` (the latter for `source_unavailable`/staleness cards). No card is produced without a witness.
*Sketch.* `rules_φ` fire only on present witnesses in `Ĝ_P(q)` or on `obs(σ)`. ∎ *Note (conceded):* this is a **provenance** property ("no fabrication"), not semantic correctness of the card's claim (see §8: fidelity ≠ truth).

**T5′ (Local Observable Soundness).** (i) Every `c∈C` is sound over `Ĝ_P(q)`. (ii) Every cross-source foreign key leaving `Ĝ_P(q)` to an unobserved/unreachable target appears in `D(q)` (subject to `δ` for invisible targets). Hence the *only* omissions are sources with **no foreign key into the observed permissioned subgraph** (and not policy-mandated).
*Sketch.* (i) by T4′ over `Ĝ_P`. (ii) `D` is read off foreign keys present in `Ĝ_P` without traversing offline sources, so unreachability cannot hide a *referenced* target. ∎ *Residual (the honest limit):* a relevant source that is **structurally disconnected** from the observed subgraph (no inbound reference, not policy-mandated) is undetectable — this is the *relevance ceiling* (§6), now stated precisely rather than hidden.

**T6 (Privacy–Coverage Impossibility) — the headline.** Define *Existence-Privacy (EP):* output is invariant under changes confined to `P`-invisible artifacts. *Coverage-Completeness (CC):* for every source `σ` relevant to `q` but unobserved, `κ` reports `σ`'s existence. **If there exists a relevant `P`-invisible source, EP and CC cannot both hold.**
*Proof.* Take `S` containing such a `σ` (relevant, `vis_P(σ)=⊥`, unobserved) and `S′ = S` with `σ` removed. `σ` is `P`-invisible, so `S|_P = S′|_P`. CC ⟹ `κ(S)` mentions `σ`, `κ(S′)` does not ⟹ `g(S)≠g(S′)` ⟹ EP violated. ∎
*Consequence:* the dial `δ` is not a wart but a **necessary control on the EP↔CC frontier**: `δ=none` gives EP + *P-relative* completeness (the maximum coverage compatible with existence-privacy); `δ=count` trades a cardinality bit; `δ=identity` chooses CC over EP. No setting escapes the frontier.

**§5.6 Guarded semantics (formal, fixing "prose").** Interpret a response as a partial-knowledge valuation over work-state propositions, `⟦·⟧ : Prop → {True, False, Unknown}`:
- `⟦ρ⟧ = True` if `ρ` is witnessed by a card in `C`;
- `⟦ρ⟧ = False` if `ρ`'s required sources are **all** `ok` in `κ` and no witness exists (negation established over complete coverage);
- `⟦ρ⟧ = Unknown` otherwise (some required source `stale`/`unreachable`, or a dangling ref bears on `ρ`).
"Absence of a card" thus maps to `False` *only under complete coverage*, else `Unknown`. The consumer obligation is the typing rule `treat Unknown ≠ False`; `κ` provides exactly the bits to evaluate it. We provide the semantics and the bits; we cannot force `A` to respect them (§8.2).

---

## 6. Relevance without Learning

`rel(v,q) = (v ∈ Ĝ_P(q)) ∧ policy_admits(v,q)`; decidable, `O(|V|+|E|)` bounded BFS. Card kinds: `overlapping_change · linked_issue_changed_after_branch · acceptance_criteria_changed · required_checklist_changed · advisory_affects_touched_dependency · related_branch_ci_failure · doc_superseded · source_unavailable`. **Relevance ceiling (the T5′ residual):** structural reachability is *sound* but not semantically complete; semantically-relevant-but-structurally-disconnected sources are out of scope by construction, mitigated only by `policy_mandated(q)`. An **untrusted client-side hint layer** may reorder/de-emphasize *already-certified* cards (any method, incl. an LLM) but **cannot add to or remove from** `C`, so it cannot perturb T1′–T6.

---

## 7. Stress Tests (revised)

| Adversary | `teamctx` guarantees | Residual |
|---|---|---|
| `Adv₁` malicious author | T3′: influences selection only via honest `φ`-features; content delivered defanged in `quote` | true-but-misleading artifacts surfaced faithfully (fidelity≠truth); `A` may ignore typing |
| `Adv₂` curious principal | T2′ (`δ=none`): output depends only on `S|_P`; invisible-target dangling refs dropped | side channels (timing/cardinality) out of value-channel model |
| `Adv₃` eclipse/network | dangling refs + `status=unreachable` make missing reachable targets **visible**; `Δ` grows | structurally-disconnected sources (T5′ residual) |
| `Adv₄` malicious agent | read-only + T2′ bound output to `P`'s permissions; signed replayable audit | cannot police `A`'s use |
| `Adv₅` compromised source | fidelity + provenance; source-signed state where available | unsigned state metadata is trusted (assumption §2) |
| `Adv₆` honest-but-wrong | deterministic `doc_superseded`, conflict ("2 sources disagree"), staleness-risk signals surface garbage *as garbage* | cannot adjudicate which source is correct |

Pattern: each adversary's *silent* success becomes a *visible* signal in `C` or `κ` — **except** the two honest residuals (structural disconnection; unsigned-metadata forgery), which we name rather than hide.

---

## 8. Limitations

1. **Fidelity, not truth** (T4′): faithfulness to observed sources, never their correctness.
2. **Agent-cooperation** (T3′/§5.6): `B` types the boundary and removes selection from the injectable surface; it cannot force `A` to honor `quote`/`Unknown`. A cooperating-consumer profile is future work; an *enforcing* consumer is a different, invariant-breaking product, excluded by design.
3. **Structural relevance ceiling** (T5′): disconnected relevant sources are undetectable; bounded only by policy.
4. **Bounded, not real-time, freshness:** under partition we choose available + honest-staleness over fresh + false (a CAP-style stance); `Δ` quantifies the cost.
5. **Metadata integrity:** where sources cannot sign state, `Adv₅` can forge `t_obs`/status; signing is the mitigation, unavailability the residual.
6. **Side channels:** timing/cardinality leakage is outside the value-channel model; mitigations (response padding, constant-time graph walk, `δ`) reduce but do not eliminate it.
7. **Permission skew:** `vis_P` fidelity depends on timely ACL mirroring; a `permission-freshness` certificate analogous to `κ` is open work.

---

## 9. Related Work

We synthesize and apply, not invent. **Reference monitors / complete mediation:** Anderson 1972; Saltzer & Schroeder 1975. **IFC / noninterference:** Denning 1976; Goguen & Meseguer 1982; Sabelfeld & Myers 2003 — T2′ is access-control-grade value-channel noninterference, *not* full IFC (reviewer-corrected). **Provenance / completeness:** W3C PROV; PASS (Muniswamy-Reddy et al., USENIX 2006); query-completeness (Motro, VLDB 1989) — `κ` is a provenance+completeness manifest specialized to partial observability. **Authenticated data structures / transparency logs:** Merkle; Certificate Transparency; Trillian — basis for §4 signed replay; we add the *dangling-reference* + EP↔CC analysis they lack for this setting. **Consistency / staleness:** Lamport 1978; CRDTs (Shapiro et al. 2011); PBS (Bailis et al. 2012) — source of `Δ` and the ingestion-order assumption. **LLM injection:** Greshake et al. 2023 (indirect injection); the **Dual-LLM** privileged/unprivileged pattern — orthogonal and *complementary*: it hardens the *consumer*; we harden *selection/delivery* and make their job checkable. **Best-effort retrieval:** RAG (Lewis et al. 2020), MCP — the paradigm we contrast.

**Positioning.** Novelty is (a) **observable soundness under partial observability** via dangling-reference certificates, (b) the **EP↔CC impossibility + declassification dial**, and (c) **payload-invariant selection** as the precise core of injection-resistant *selection*. The packaging (provenance + freshness + signature) is, as reviewers noted, standard.

---

## 10. Discussion

The honest contribution: **a context system for an acting agent cannot be both existence-private and coverage-complete; the best achievable is observable soundness — soundness over the observed, permitted subgraph plus an explicit, structurally-bounded statement of what leaves it — and a principled dial over the residual.** That is less than "certified omniscience" and more useful than best-effort recall: it is falsifiable, replayable, and honest about a boundary that recall-based systems cannot even name. Whether the EP↔CC frontier admits a tighter quantitative characterization (e.g., an information-theoretic leakage bound per `δ`) is the most promising open problem.

**Open problems.** Permission-freshness certificates; an information-theoretic treatment of `δ`-leakage; a verified cooperating-consumer profile; mechanized proofs of T1′–T6; empirical measurement of the relevance ceiling (what fraction of behavior-changing context is structurally reachable at depth `k`?).

---

## 11. Conclusion

`teamctx` v0.2 reframes agent context as deterministic mediation under *partial observability*. It returns source-backed cards plus a coverage certificate that is sound over what it observed and explicit about what it did not — and it proves that no such mediator can be both private about the invisible and complete about the relevant. It does not promise truth or omniscience. It promises something checkable: it will not lie to your agent by omission *within the region it can see*, and it will tell you, by construction, where that region ends.
