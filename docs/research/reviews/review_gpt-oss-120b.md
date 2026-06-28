**Referee Report – “Certified Context for Autonomous Coding Agents – A Deterministic Mediation Protocol with Coverage Guarantees”**  
*Submitted to the Systems & Security track (SOSP/OSDI/IEEE S&P/USENIX Security/PLDI).*  

---

### 1. Summary (2 sentences)

The paper proposes a deterministic broker, **teamctx**, that mediates between an autonomous coding agent and a set of “sources of truth” (git, issue tracker, docs, CI).  The broker returns a bounded set of *context cards* together with a **coverage certificate** κ that enumerates which sources were consulted, their timestamps and reachability status, and the authors claim five theorems (determinism, permission‑noninterference, evidence/instruction separation, soundness, and “no‑silent‑omission”).

---

### 2. Soundness of Theorems 1‑5  

| Theorem | Claim | Why the sketch is insufficient / false | Missing / implicit assumptions |
|--------|-------|----------------------------------------|--------------------------------|
| **1 (Determinism)** | `g(S,q,P)` is a pure function of its arguments, therefore invariant across invocations. | The proof assumes that **all** inputs to `g` are pure, but the *snapshot* `S` is built from *event‑sourced* logs that may contain nondeterministic ordering (e.g., concurrent webhooks). The paper does not prove that the fold over logs yields a *canonical* snapshot independent of delivery order. Without a total order (e.g., vector clocks) the same logical state may be represented by different `S`, violating determinism. | *Assumption*: source logs are totally ordered and delivered without loss. No discussion of clock skew, duplicate events, or eventual consistency. |
| **2 (Permission non‑interference)** | If two snapshots agree on the `P`‑visible subset, the output is identical. | The theorem treats `vis_P` as an *oracle* that returns a Boolean per artifact. In practice `vis_P` is implemented by querying the source ACLs, which may be *stateful* (e.g., rate‑limited, cached). Moreover, the proof ignores the **size of κ**: the certificate contains `t_obs(σ)` for each required source, which can differ even when `S|_P` is equal (e.g., one source is reachable, another is temporarily unreachable). Thus the observable output (including timing) can leak the existence of hidden artifacts via the *absence* of a source entry. | *Assumption*: `vis_P` is instantaneous, side‑effect‑free, and the set of required sources `Req(q)` is independent of hidden artifacts. No treatment of timing or cardinality side‑channels. |
| **3 (Evidence/Instruction separation)** | Source bytes only appear inside `quote(·)`; the broker’s control flow never depends on payload content. | The claim that “payload is control‑flow‑irrelevant” holds only for the **broker**. The *card ranking* step (`rank`) may use fields such as `severity` that are derived from *metadata* (e.g., `type`, `freshness`). However, `freshness` is computed from `t_obs(σ)` which itself may be influenced by *network delays* that an adversary can manipulate (Adv₃). Consequently, an attacker can affect which cards are emitted by forcing a source to be marked *stale* or *unreachable*, thereby changing the *set* of cards. The proof sketch does not address this indirect channel. | *Assumption*: all metadata used for rule selection is trustworthy and cannot be manipulated by an adversary. No explicit integrity guarantees for `t_obs`. |
| **4 (Soundness / no fabrication)** | Every emitted card has a witness artifact in the permission‑filtered snapshot. | The definition of “witness” is vague: the card contains a *provenance* field that may list multiple artifacts, but the paper never requires that **all** listed artifacts be present in `S|_P`. A malicious source could create an artifact whose body is empty but whose metadata (e.g., `type=doc`, `scope=…`) triggers a rule, resulting in a card that *appears* to be backed by a non‑existent artifact. The proof sketch assumes the rule engine validates existence, but no formal invariant is stated. | *Assumption*: the rule engine has a *well‑formedness* invariant that every rule precondition includes a concrete artifact identifier that is checked against `S|_P`. |
| **5 (No‑Silent‑Omission)** | Every response carries κ that lists *all* required sources, so the broker never silently omits a source. | The definition of `Req(q)` is “sources owning nodes in `R_k(q)` **plus** policy‑mandated sources.” The paper does not prove that **policy‑mandated sources** are *complete*: a policy may say “if a PR touches a path that matches `*.proto`, also consult the protobuf schema repository”. If the policy is mis‑specified, a required source will be omitted from `Req(q)` and consequently from κ, yet the protocol will still claim “no silent omission”. Moreover, the certificate does not hide *which* sources are required; an adversary can infer the existence of a hidden source by observing that κ contains fewer entries than the maximum possible cardinality (a classic “coverage‑size” side‑channel). | *Assumption*: the policy language is expressive enough to capture *all* relevant dependencies, and the policy is correct. No formal completeness argument is provided. |

**Overall assessment:** The theorems are *plausibly true* under a set of strong, undocumented assumptions (total order of events, immutable ACLs, trustworthy metadata, complete policy). The paper’s proof sketches are circular: they assume the very properties they aim to prove (e.g., that `vis_P` is side‑effect‑free, that `t_obs` is untamperable). Without explicit invariants and a mechanized proof, the theorems remain unsubstantiated.

---

### 3. Central Contribution – Coverage Certificate & “No‑Silent‑Omission”

The **coverage certificate** κ is essentially a *metadata dump* of which sources were consulted, their timestamps, and a reachability flag. Similar constructs already exist in:

* **Transparency logs** (Certificate Transparency, Trillian) – a signed hash of the set of certificates consulted.  
* **Verifiable data structures** for *provable query* (e.g., Merkle‑tree based inclusion proofs).  
* **Provenance systems** (e.g., Apache Atlas, OpenLineage) that attach a “lineage” graph to a data product.

What is *new* here is the coupling of κ with a *typed evidence channel* and the claim that the absence of a card is a *typed obligation* rather than a “clearance”. However, the paper merely **relocates** the “absence‑as‑clearance” problem: the consumer of κ must now interpret “no card for source σ” as “unknown for σ”. This is exactly the same semantic gap that the authors criticize in best‑effort retrieval, only shifted from the *agent* to the *broker’s client*. The formal semantics of the guarded claim `⟦⟨C,κ⟩⟧` is left as an informal English description; there is no algebraic definition, nor a proof that the semantics is compositional (e.g., that two independent κ’s can be merged without ambiguity).

Consequently, the contribution is **incremental**: a modest packaging of already‑known provenance information with a signature, plus a policy‑driven reachability analysis. It does **not** “dissolve” the absence‑as‑clearance fallacy; it merely makes the *unknown* region explicit, which is useful but not a breakthrough.

---

### 4. Non‑interference (Theorem 2) – Is it genuine?

The theorem is essentially a *refinement* of classic **access‑control**: the broker filters the snapshot before any computation. This is a textbook *reference monitor* property (Anderson 1972) and does not provide the stronger *information‑flow* guarantees that modern non‑interference literature demands (e.g., *declassification* of aggregate statistics).  

**Side‑channel objection:** κ includes the *count* of reachable sources and the *maximum staleness* Δ. An adversary controlling the timing of source failures can modulate these values, thereby leaking coarse information about hidden artifacts (e.g., “if I make source σ unreachable, the response time drops by 30 ms”). The paper acknowledges timing leaks in §8.5 but does not bound them, nor does it propose mitigation (e.g., padding responses). This violates the spirit of non‑interference: the observable output (including timing) must be independent of hidden data, not just the *payload*.

Thus Theorem 2 is, at best, a *trivial* statement about access control, not a substantive non‑interference result.

---

### 5. Evidence/Instruction Separation (Theorem 3) – Soundness?

The claim that source payload never influences control flow is true **only** for the broker’s internal logic. The *agent* receives the quoted payload and may decide to *execute* it (e.g., by downloading a URL found in a quoted field). The authors explicitly note that the *agent‑cooperation* assumption is outside the threat model. This caveat **nullifies** the practical impact of the theorem: the most dangerous class of injection attacks (prompt‑injection, command‑injection) are precisely those where the downstream consumer treats source data as code. If the consumer does not enforce the typing discipline, the broker’s guarantee is moot.

Moreover, the proof sketch does not address **implicit flows**: the presence or absence of a card can itself be a covert channel. For instance, a rule that emits a “high‑severity” card only when a particular keyword appears in a doc will cause the *card set size* to vary with the payload, thereby leaking information about the payload even though the payload is never directly used in control flow. The paper’s “no‑silent‑omission” property is intended to mitigate this, but as argued in §3, it merely makes the omission *observable*, not *non‑existent*.

Therefore Theorem 3 is **over‑stated**; its practical relevance hinges on a cooperation assumption that the paper deliberately excludes from its threat model.

---

### 6. Prior Art – Is this already known?

1. **Reference Monitor + Provenance** – The combination of a deterministic filter, provenance tagging, and a signed response is essentially what *Google’s Tricorder* (Kumar et al., OSDI 2022) does for build‑time reproducibility.  
2. **Verifiable Data Retrieval** – The *Authenticated Data Structures* literature (e.g., Merkle‑RB‑Tree, Bender et al., PODC 2020) provides *inclusion proofs* that a set of keys was retrieved from a snapshot, together with a *range proof* that no other keys exist in a given interval. This directly yields a “coverage” guarantee without the need for a bespoke protocol.  
3. **Policy‑driven Data Mediation** – *Furthemore* (Zhang et al., USENIX Security 2021) implements a policy engine that, given a request, computes a minimal set of data items and returns a signed “access‑decision” together with a *data‑dependency graph*. The graph plays the same role as κ.  
4. **Secure Information Flow for LLMs** – Recent work on *Prompt‑Injection Resistance* (e.g., “LLM‑Guard” by Liu et al., CCS 2023) already separates *evidence* (user‑provided text) from *instructions* (system‑generated prompts) via a typed DSL, and proves that the LLM cannot be coerced into executing user payloads.  

All of the above achieve the same *core* properties (deterministic mediation, provenance, signed attestations) and, crucially, they provide **formal models** that include the missing invariants (total order, integrity of timestamps, completeness of policy). The present paper does not cite these works, nor does it explain why its approach is fundamentally different. Consequently the claim of novelty is **unsubstantiated**.

---

### 7. Killer Objection & Required Fix

**Killer objection:** The paper’s security theorems rely on *unstated* invariants (total ordering of events, immutable ACLs, trustworthy metadata) that are *known to be impossible* in the heterogeneous, eventually‑consistent environments the authors target (GitHub, Jira, CI). Without a rigorous treatment of these invariants, the theorems are vacuous; the protocol can be trivially subverted by an adversary who delays a webhook or tampers with a source’s `t_obs`.  

**Most important fix:** Provide a **formal, end‑to‑end proof** that the *snapshot* `S` is *canonical* despite out‑of‑order events and that the *coverage certificate* κ is *sound* even when sources are partially unavailable. This requires:

1. Defining a **total order** (e.g., Lamport timestamps or vector clocks) for events and proving that the fold over logs yields a *unique* snapshot irrespective of delivery order.  
2. Extending the threat model to include **integrity attacks on metadata** (timestamps, status flags) and showing that κ can be *cryptographically attested* (e.g., via source‑signed timestamps) rather than merely trusted.  
3. Formalizing the semantics of `⟦⟨C,κ⟩⟧` as a *partial‑knowledge* lattice, and proving that the “no‑silent‑omission” property is *information‑theoretically* satisfied (i.e., the adversary’s view is bounded by κ).  

Only after these gaps are closed can the claimed theorems be taken seriously.

---

### 8. Verdict  

**Reject (major‑revision required).**  

*Core contribution:* The paper presents a deterministic broker that returns a signed set of provenance‑tagged “context cards” together with a lightweight coverage certificate. While the engineering effort is non‑trivial, the security claims are under‑specified, the novelty is marginal with respect to existing provenance and verifiable‑query systems, and the formal theorems rest on unrealistic assumptions. Substantial revisions, particularly a rigorous treatment of event ordering, metadata integrity, and a formal semantics for the guarded claim, are needed before the work can be considered a solid contribution to the security of autonomous coding agents.