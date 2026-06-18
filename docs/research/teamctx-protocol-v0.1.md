# Certified Context for Autonomous Coding Agents
### A Deterministic Mediation Protocol with Coverage Guarantees

*Working paper v0.1 — written in role as a Distributed Systems & Security research pair (PhD candidate + advisor). This is an internal stress-testing document, not a publication. Claims are stated to be attacked.*

---

## Abstract

Autonomous coding agents act on the live state of a software team — open pull requests, changed acceptance criteria, updated process docs — yet they begin each session blind to it. The prevailing remedy is *best-effort retrieval*: dump source material (RAG, long context, agent memory) into the model and hope it attends to the right facts. Best-effort retrieval has three structural defects: it is **unverifiable** (you cannot prove what the agent could and could not have seen), it **conflates current with correct** and **absent with safe**, and it is a **prompt-injection delivery channel** by construction.

We reframe the problem as **certified context mediation**. We define a deterministic protocol, `teamctx`, that sits between untrusted systems-of-record and an acting agent and returns a small set of source-backed *context cards* together with a **coverage certificate** `κ`. We prove (sketch) four properties — *determinism*, *permission noninterference*, *evidence/instruction separation*, and *no-silent-omission* — and show they follow from a single design choice: the card generator is a pure function over a permission-indexed snapshot, with source content confined to a typed, non-imperative channel. The coverage certificate makes the protocol's *negative* claims explicit and bounded: `teamctx` cannot say "all clear," only "no conflict over the observed, permitted region described by `κ`." We give an adversary-by-adversary security analysis, state the limitations honestly (fidelity is guaranteed, *truth* is not), and position the work against reference monitors, information-flow control, language-theoretic security, and bounded-staleness consistency.

**Contributions.**
1. A formalization of agent context as *certified mediation* rather than best-effort retrieval.
2. The **coverage certificate** `κ` and the **No-Silent-Omission** property, a calculus in which "I don't know" is typed and bounded — the formal dissolution of the *absence-as-clearance* fallacy.
3. A proof sketch that **determinism + typed channels + permission-indexed inputs** jointly yield reproducible audit, noninterference privacy, and injection-resistance — properties usually pursued separately.
4. A **decidable, learning-free relevance predicate** based on typed blast-radius reachability, with an explicit *relevance ceiling* and an untrusted client-side hint layer that cannot perturb the certified set.

---

## 1. Introduction

A unit of software work is a task on a branch. Its *truth* — the facts that should change what gets written — is scattered across a forge (PRs/MRs), a tracker (issues, acceptance criteria), docs (process rules), and CI. Humans discover these facts late, after the collision; autonomous agents discover them never, because each session starts cold and the agent confidently fills gaps it cannot see.

The dominant response is to widen the agent's intake: larger context windows, retrieval pipelines, persistent "memory." This treats context as a *recall* problem. We argue it is a *mediation* problem with three hard requirements that recall-based systems cannot satisfy:

- **Verifiability.** A reviewer (human or automated) must be able to reproduce exactly what the agent was shown and why. Non-deterministic retrieval over a black-box model is, by definition, not reproducible.
- **Permission fidelity.** The agent must see only what the requesting human is permitted to see, and the system's output must not leak the existence of what it may not see.
- **Trust boundary.** Source text is written by potentially adversarial third parties (anyone who can open an issue). It must reach the agent as *evidence*, never as *instructions*.

`teamctx` is a protocol designed so that these three requirements, plus a fourth — *honesty about what was not observed* — are **structural properties with proofs**, not best-effort behaviors.

### 1.1 Why determinism is load-bearing, not nostalgic

A natural objection: "Won't 10M-token windows and cheap inference make a deterministic broker obsolete? Just give the model everything." This conflates *capacity* with *authority*. A model with more context can ingest more; it cannot *prove* what it was allowed to know, *certify* what it failed to fetch, or *guarantee* that hostile source text never crossed into its instruction stream. Capacity does not produce certificates. The contribution of this paper is the certificate.

---

## 2. Setting and Threat Model

### 2.1 Entities

- **Principal** `P` — a human, with an identity and a set of permissions across sources.
- **Agent** `A` — an autonomous tool acting *on behalf of* `P`. `A` is untrusted by the protocol.
- **Broker** `B` — the `teamctx` implementation. Trusted, but minimized: deterministic, read-only, no learned components in the certified path.
- **Sources** `Σ = {σ₁ … σₙ}` — forge, tracker, docs, CI. Each exposes (a) artifacts, (b) a permission oracle, (c) an event stream. Sources are *semi-trusted*: trusted to report their own state, **not** trusted for the *content* of artifacts authored within them.

### 2.2 Trust classification

- **Trusted inputs:** local policy, connector configuration, the deterministic card rules, permission results from sources.
- **Untrusted inputs (data, never instructions):** PR/issue/doc titles and bodies, comments, commit messages, any artifact text.

### 2.3 Adversaries (analyzed in §7)

- `Adv₁` *Malicious source author*: can create artifacts (open a PR, file an issue, edit a doc) containing injection payloads, malware links, or misleading content.
- `Adv₂` *Curious principal*: tries to use `B`'s output to infer artifacts they are not permitted to see.
- `Adv₃` *Network / eclipse adversary*: delays or drops source events to make stale state appear current.
- `Adv₄` *Malicious agent*: tries to exceed its principal's authority or exfiltrate.
- `Adv₅` *Compromised connector/source*: lies about artifact state.
- `Adv₆` *Honest-but-wrong source* ("garbage-in"): non-adversarial but stale/incorrect artifacts (a Jira ticket marked Done that isn't).

---

## 3. Formal Model

### 3.1 Artifacts and snapshots

An **artifact** `a` is a tuple
`a = (id, type, scope, state, t_created, t_updated, provenance, sensitivity, trust, body)`
where `type ∈ {pr, issue, doc, check, …}`, `scope` is a set of subject references (paths, symbols, issue keys, components), `trust ∈ {untrusted}` for all source-authored content, and `body` is opaque source text.

A **snapshot** `S` at broker-time `t` is a finite set of artifacts together with, for each source `σ`, an **observation record** `obs(σ) = (t_obs(σ), status(σ))`, `status ∈ {ok, stale, unreachable}`. The snapshot is maintained as an **event-sourced materialized view**: source webhooks/polls append immutable events to a per-source log; `S` is a deterministic fold over the logs. This gives time-travel (`S` *as of* any `t`) and `O(1)` amortized update per event.

### 3.2 Permissions

Each source exposes a permission oracle `vis_P : Artifact → {⊤, ⊥}`. The **`P`-restriction** of a snapshot is
`S|_P = { a ∈ S : vis_P(a) = ⊤ }`.
We treat `vis_P` as authoritative; §8 discusses ACL-skew.

### 3.3 Request context and blast radius

A **request** is `q = (P, repo, branch, base, paths, symbols, linked_refs, session, t)`.

The typed **artifact graph** `G = (V, E)`: nodes are artifacts and work targets; edges are *deterministic* relations (`pr —modifies→ path`, `branch —references→ issue`, `issue —links→ doc`, `doc —governs→ component`, `pr —overlaps→ pr`). The **seed** `seed(q) ⊆ V` is the set of nodes named by `q` (touched paths, resolved symbols, linked refs). The **blast radius** is bounded reachability:
`R_k(q) = { v ∈ V : dist(seed(q), v) ≤ k over admitted edge types }`.
`R_k` is computable by bounded BFS in `O(|V| + |E|)`, in practice bounded by `k` and node degree.

### 3.4 Cards and the coverage certificate

A **context card** is
`c = (kind, severity, refs, reason, freshness, confidence, source_body_state, agent_instruction, provenance)`
where `agent_instruction ∈ {evidence_only, verify_before_relying, apply_when_in_scope}` is drawn from a **fixed broker vocabulary** (independent of `S`), `source_body_state ∈ {status_only, openable, blocked, unavailable}`, and `provenance` points to the witness artifact(s).

Let `Req(q) ⊆ Σ` be the sources required to answer `q` (those owning nodes in `R_k(q)`, plus policy-mandated sources). The **coverage certificate** is
`κ(q) = { (σ, t_obs(σ), status(σ)) : σ ∈ Req(q) }`.
Define **staleness** `Δ(q) = t − min{ t_obs(σ) : status(σ)=ok }` and **coverage** `cov(q) = |{σ : status=ok}| / |Req(q)|`.

### 3.5 The card generator

The certified output is produced by a pure function
`g(S, q, P) = ⟨ C, κ ⟩`, with `g = render ∘ rank ∘ rules ∘ π_P`,
where `π_P` is the permission filter (`π_P(S) = S|_P`), `rules` applies the deterministic card rules over `R_k(q)`, `rank` is a deterministic severity ordering, and `render` emits typed fields. **`g` performs no I/O, reads no clock (time is a parameter), and contains no learned component.**

---

## 4. The Protocol

### 4.1 Messages

```
A → B :  CtxRequest { principal_token, repo, branch, base,
                      paths[], symbols[], linked_refs[], session, t }
B → A :  CtxResponse { cards: Card[],          // the certified set C
                       coverage: κ,            // mandatory
                       staleness: Δ, coverage_ratio: cov,
                       snapshot_digest, response_sig }   // see §4.3
```

`CtxResponse` has **no variant** that omits `coverage`. There is no "all clear" message; the absence of a high-severity card is interpretable only in conjunction with `κ`.

### 4.2 Pipeline (all stages deterministic)

1. **Identity resolution.** Resolve `P` behind `A`; obtain `P`'s per-source credentials (impersonation; least privilege; metadata scopes).
2. **Blast-radius computation.** Build `seed(q)`, compute `R_k(q)` over the materialized graph.
3. **Permission filter `π_P`.** Drop artifacts with `vis_P = ⊥` *before* any rule runs.
4. **Rule evaluation.** Apply deterministic card rules to `R_k(q) ∩ S|_P` (§6).
5. **Quarantine + defang.** Any surfaced source bytes are wrapped by the `quote(·)` constructor (§4.4); URLs/code rendered inert; bodies default to `status_only`.
6. **Certificate assembly.** Emit `⟨C, κ⟩` with `Δ`, `cov`, `snapshot_digest`.

### 4.3 Custody (optional cryptographic binding)

`B` may sign `H(C ‖ κ ‖ H(q) ‖ snapshot_digest)`. The signature makes a response **reproducible and tamper-evident**: given the snapshot log up to `snapshot_digest` and `q`, any auditor recomputes `g` and checks equality. This realizes "context with custody": the agent's claimed context is a verifiable artifact, not a transcript assertion. (Connects to transparency-log / verifiable-computation practice.)

### 4.4 Channel typing (the trust boundary, made syntactic)

The agent-facing payload is partitioned into two channels:

- **Instruction channel `I`** — `agent_instruction` and other broker-authored fields, drawn from a fixed finite vocabulary `𝒱` with `𝒱 ∩ (source bytes) = ∅`.
- **Evidence channel `E`** — every field carrying source-derived bytes appears only as `quote(meta, payload)`, where `payload` is opaque and `meta` is typed broker metadata (freshness, provenance, permission).

The only constructor admitting source bytes is `quote(·)`. No source byte may appear in `I`.

---

## 5. Properties and Guarantees

> Proof *sketches*; the point of v0.1 is to expose them to attack, not to claim QED.

**Theorem 1 (Determinism / referential transparency).** For fixed `S, q, P`, `g(S,q,P)` is invariant across invocations, agents, and wall-clock time.
*Sketch.* `g` is a composition of pure functions; all ambient effects (clock, network, randomness) are excluded from the certified path; `S` and `t` are explicit parameters. ∎

**Theorem 2 (Permission noninterference).** If `S|_P = S′|_P` then `g(S,q,P) = g(S′,q,P)`. Equivalently, `g` depends only on the `P`-visible sub-snapshot.
*Sketch.* `π_P` is the first stage and `π_P(S) = S|_P`; downstream stages are pure functions of `π_P`'s output. Hence artifacts in `S \ S|_P` cannot affect output. *Corollary:* `B`'s output reveals no information about artifacts `P` cannot see — including their existence. (Side channels addressed in §7/§8.) ∎

**Theorem 3 (Evidence/instruction separation; injection-resistance at the broker).** No source-derived byte occupies an imperative position in `B`'s output, and source *content* cannot influence which cards are produced.
*Sketch.* (i) By construction, source bytes enter output only via `quote(·) ∈ E`; `I` is drawn from `𝒱`, disjoint from source bytes. (ii) `rules`/`rank` branch only on typed metadata (type, scope, freshness, permission), never on `payload` bytes; thus `payload` is control-flow-irrelevant in `B`. Therefore an injection payload can be *carried* (as quoted evidence) but can neither *command* `B` nor *steer* card selection. ∎
*Honest caveat (see §8):* this bounds `B`. It does **not** force a downstream agent to honor the typing; it gives the agent a machine-checkable boundary it *can* enforce (e.g., refuse to execute `quote(·)` content), and it minimizes the injected surface to defanged, clearly-labeled evidence.

**Theorem 4 (Soundness / no fabrication).** Every card `c ∈ C` has a witness artifact `a ∈ S|_P` with `provenance(c) ∋ a`. `B` emits no claim lacking a source witness.
*Sketch.* `rules` only constructs a card when its triggering artifacts are present in `R_k(q) ∩ S|_P`; there is no generative step. ∎

**Theorem 5 (No-Silent-Omission).** Every response carries `κ` over `Req(q)`; `B` has no message asserting an unqualified negative. The semantics of a response is the *guarded claim*
`⟦⟨C, κ⟩⟧ = "C is sound over region(κ); outside region(κ): unknown."`
*Sketch.* `CtxResponse` is the sole response type and `coverage` is non-optional; `Req(q)` is computed from `R_k(q)` independently of which sources happened to be reachable, so an unreachable required source appears in `κ` with `status=unreachable` rather than being silently excluded. ∎

**Corollary (Absence is bounded, not clearance).** The agent cannot read "no conflict card" as "no conflict." It can only read it as "no conflict among sources marked `ok` in `κ`; sources marked `stale`/`unreachable` are unknown." The `absence-as-clearance` failure becomes a *typed obligation* on the consumer.

---

## 6. Relevance without Learning

`rules` decides relevance by a **decidable predicate**, not a model:
`rel(v, q) = (v ∈ R_k(q)) ∧ policy_admits(v, q)`,
where `policy_admits` is a team-authored, version-controlled policy (`.teamctx` blast-radius rules: path globs, components, labels, ownership, required-link constraints). Card *kinds* are a fixed taxonomy of high-value, structurally-detectable failures:

`overlapping_change · linked_issue_changed_after_branch · acceptance_criteria_changed · required_checklist_changed · advisory_affects_touched_dependency · related_branch_ci_failure · doc_superseded · source_unavailable`.

**Relevance ceiling (stated, not hidden).** Structural reachability is *sound* (a surfaced overlap is real) but not *semantically complete*: "this Confluence rule should change your implementation" may not be structurally reachable. We bound the claim to structural relevance and expose a separate, **untrusted client-side hint layer** that may re-order or de-emphasize *already-certified* cards using any method (including an LLM) — but **cannot add to or remove from** the certified set `C`. Thus hints never perturb Theorems 1–5; they only affect presentation. Complexity: `rel` is `O(|R_k(q)|)`; the certified set is independent of the hint layer.

---

## 7. Stress Tests (Security Analysis)

| Adversary | Goal | What `teamctx` guarantees | What it does **not** |
|---|---|---|---|
| `Adv₁` malicious source author | Inject instructions / malware / mislead | T3: payload reaches agent only as defanged `quote(·)`; cannot command `B` or steer card selection; links inert; bodies `status_only` | Cannot stop a *true-but-weaponized* artifact from being faithfully surfaced (truth-judgment is downstream); cannot force the *agent* to honor the boundary |
| `Adv₂` curious principal | Infer artifacts beyond permission | T2: output depends only on `S|_P`; existence of hidden artifacts not revealed | Cardinality/timing side channels (§8); mitigated by permission-aware `κ` |
| `Adv₃` eclipse / network | Make stale look fresh | T5: stale/unreachable sources surface in `κ`; `Δ` grows visibly; **no false freshness** | Cannot *prevent* staleness (CAP); chooses availability + honest staleness over false certainty |
| `Adv₄` malicious agent | Exceed authority / exfiltrate | Read-only + T2 bound output to `P`'s permissions; signed responses give audit | Cannot police what the agent does with what its principal could already see |
| `Adv₅` compromised connector/source | Lie about state | **Fidelity** to source + provenance for forensics; connector attestation where available | Cannot guarantee source *correctness* (fidelity ≠ truth) |
| `Adv₆` honest-but-wrong source | Mislead via stale artifacts | Deterministic *staleness-risk* and *conflict* signals (e.g., `doc_superseded`, "2 sources disagree", "doc unedited 300d while code changed N×") surface garbage **as garbage** | Cannot adjudicate which conflicting source is correct |

The recurring pattern: `teamctx` converts each adversary's *silent* success into a *visible* signal (in `C` or `κ`). It does not claim to prevent every harm; it claims to make the relevant harms **non-silent and attributable**.

---

## 8. Limitations (the honest section)

1. **Fidelity, not truth.** Theorems 4–5 certify faithfulness to observed sources, never that sources are correct. The `truth` of a Jira ticket is out of scope by construction; we surface *change, conflict, and staleness*, and refuse to assert correctness.
2. **Agent-cooperation assumption.** T3 bounds `B`, not `A`. Full end-to-end injection-resistance requires the consuming agent to honor evidence/instruction typing. `teamctx` provides the mechanism and minimizes surface; enforcing it on `A` (a blocking client) is a different, invariant-breaking product and is deliberately excluded.
3. **Relevance ceiling.** Structural relevance under-covers semantic relevance; the untrusted hint layer mitigates UX but cannot (by design) repair completeness without sacrificing Theorems 1–2.
4. **Freshness is bounded, not real-time.** Under partition we choose available-and-honest over fresh-and-false (a CAP-style stance); `Δ` quantifies the cost.
5. **Permission skew.** `vis_P` fidelity depends on timely mirroring of source ACLs; a `permission-freshness` certificate analogous to `κ` is required to bound the window between an ACL change and its reflection (open problem).
6. **Side channels.** Coverage cardinality and response timing leak coarse information; `κ` must be permission-scoped (do not reveal counts of invisible sources).

---

## 9. Related Work

- **Reference monitors / complete mediation** (Anderson 1972; Saltzer & Schroeder 1975): `B` is a read-only monitor; we add determinism + certificates.
- **Information-flow control & noninterference** (Denning 1976; Goguen & Meseguer 1982; Sabelfeld & Myers 2003): Theorem 2 is a noninterference property over a permission lattice.
- **Language-theoretic security / injection** (Sassaman et al.; Greshake et al. 2023, *indirect prompt injection*): Theorem 3 is a typed evidence/instruction separation; we treat source text as a data language, never a command language.
- **Capability security** (Miller 2006): impersonated, least-privilege source access as capabilities.
- **Consistency & time** (Lamport 1978; vector clocks; Shapiro et al. CRDTs 2011; Bailis et al. PBS 2012): event-sourced materialized view + bounded-staleness `Δ`.
- **Transparency logs / verifiable computation** (Certificate Transparency; Merkle): §4.3 signed, replayable responses.
- **Retrieval-augmented generation & agent memory** (Lewis et al. 2020; MCP 2024): the incumbent *best-effort* paradigm we contrast with *certified mediation*.

**Positioning.** We do not invent IFC, reference monitors, or bounded staleness. The contribution is their *synthesis* for the agent-context problem, plus (a) the **coverage certificate** and **No-Silent-Omission** calculus and (b) the result that four properties usually engineered separately fall out of a single determinism + typed-channels + permission-indexing design.

---

## 10. Discussion: is there a breakthrough here?

Measured claim: the **engineering insight** is that *agent context should be a certified, falsifiable artifact, and that "honest absence" is the property best-effort systems can never provide.* Larger context windows improve recall monotonically and still cannot produce `κ`. The coverage certificate is small, cheap, and — as far as current practice goes — an unaddressed primitive: today's agent-context stacks fail *silently* on partial observability, which §7 shows is exactly where the worst outcomes (confident wrong action on stale/blocked state) occur.

If a single sentence survives review, let it be: **a context system for an acting agent must return not only what it found, but a bounded, machine-checkable statement of what it could not see.**

### Open problems
- A `permission-freshness` certificate bounding ACL skew (§8.5).
- Empirical characterization of the relevance ceiling: how much of real, behavior-changing context is structurally reachable at depth `k`?
- A separate **coordination layer** for multi-agent write-races (a lease calculus), kept outside the read-only certified core.
- Formal verification of connector correctness (the trusted-mirroring assumption).

---

## 11. Conclusion

`teamctx` reframes context for autonomous coding agents from best-effort retrieval to certified mediation: a deterministic, permission-faithful, injection-resistant protocol that returns source-backed cards **and a coverage certificate that bounds its own ignorance**. The guarantees are structural consequences of one decision — a pure card generator over a permission-indexed snapshot with a typed evidence channel — and they degrade *visibly*, never silently, under adversarial conditions. The protocol does not promise truth or omniscience. It promises something rarer and checkable: it will not lie to your agent by omission.
