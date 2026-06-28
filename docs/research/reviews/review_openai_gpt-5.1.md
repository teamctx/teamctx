1. Summary of claims  
The paper proposes a deterministic, read‑only “context broker” (`teamctx`) that mediates between untrusted project artifacts and an LLM agent, producing a set of typed “cards” plus a coverage certificate `κ` that is supposed to make explicit what sources were and were not observed. The core claimed technical contributions are: (i) a formalization of context as certified mediation rather than best‑effort retrieval, (ii) four properties (determinism, permission noninterference, evidence/instruction separation, and no‑silent‑omission) allegedly obtained “for free” from a pure function over a permission‑indexed snapshot with typed channels, and (iii) a “No‑Silent‑Omission” calculus in which absence is never silently taken as clearance.

---

2. Soundness of Theorems T1–T5

I’ll go theorem by theorem and point out where the reasoning is underspecified or circular, and what extra assumptions are silently required.

**Theorem 1 (Determinism / referential transparency).**  
Claim: “For fixed `S, q, P`, `g(S,q,P)` is invariant across invocations, agents, and wall-clock time.” Proof sketch: “`g` is a composition of pure functions; all ambient effects … are excluded.”

Issues:

- This is purely definitional. You *define* `g` as pure and side‑effect free, but you never actually define `rules` or `rank` in a way that would let one check they have no hidden dependence on e.g. wall‑clock time, environment variables, or external caches. As long as “card rules” are abstract black boxes, Theorem 1 is trivially true if you assume purity and false if you don’t. The “proof” is “assume the conclusion.”
- You gloss over sources of nondeterminism that are not modeled: concurrency in updating `S` (“event‑sourced materialized view”), versioning of the rule set, and configuration changes. You let `t` be a parameter, but you do not explicitly require that `snapshot_digest` fully determines `S(t)` *and* the effective rule version and policy. In practice, if rules change between audits, `g(S,q,P)` will not be re‑computable without pinning rule versions per snapshot. This is a missing assumption.
- You do not specify what happens if `Req(q)` depends on the structure of `G` that itself is built from `S`. If `G` construction is not totally deterministic given `S|_P`, Theorem 1 fails. That’s another implicit assumption.

Conclusion: T1 is salvageable but currently vacuous: it’s just assuming purity for all pipeline components without specifying any semantics that would make this checkable. To make it sound, you need (a) a formal semantics of `rules`, `rank`, `render` and `G` construction, and (b) a versioning story tying them into `snapshot_digest`.

---

**Theorem 2 (Permission noninterference).**  
Claim: “If `S|_P = S′|_P` then `g(S,q,P) = g(S′,q,P)`.” Proof: `π_P` is applied first.

Issues:

- Given your definition `g = render ∘ rank ∘ rules ∘ π_P`, the theorem is literally by algebraic substitution: if `π_P(S) = π_P(S')`, downstream behavior is identical. So internally, as a property of the *function* as defined, it’s fine.
- However, the important security claim you derive, “output reveals no information about artifacts `P` cannot see, including their existence”, is much stronger and currently false as stated because you systematically ignore side channels:
  - `κ(q)` encodes `Req(q)`. If `Req(q)` is computed using global knowledge of sources or graph structure including hidden artifacts, `κ` may leak that “some other source exists that you don’t have rights for.” You hint at this in §8.6 (“`κ` must be permission‑scoped”) but you don’t spell out conditions under which it holds.
  - Timing and cardinality side channels are not modeled. You acknowledge them but still label the corollary as noninterference *tout court*. This is at best termination‑insensitive noninterference on the *value* channel, with uncontrolled timing and resource side channels.
- There is no threat model addressing colluding principals: `Adv₂` is a single principal, but two principals `P1` and `P2` with different `S|_P` and shared view of `κ` + timing could infer information about hidden artifacts by differencing responses. Classic noninterference definitions (Goguen–Meseguer 1982, Sabelfeld–Myers 2003) make this explicit and you do not.

Conclusion: T2, as a *functional property* of `g`, holds given your construction; as a *security* noninterference claim it is overstated. You essentially prove an access‑control‑style data dependence property and then rhetorically upgrade it to full noninterference, ignoring declassification and side channels.

---

**Theorem 3 (Evidence/instruction separation; injection-resistance at the broker).**  
Claims: (i) “No source-derived byte occupies an imperative position in `B`'s output” and (ii) “source content cannot influence which cards are produced.”

Payload–control separation:

- The first part is defensible *if* your output type system is actually enforced at all construction points, and `quote` is the only constructor that ever takes payload bytes. But this is again axiomatic: you do not give a formal language or typing judgment. “By construction” is hand‑wavy without a formal grammar and a guarantee that `rules` cannot, for instance, embed a snippet of source text into `agent_instruction` as a formatting artifact.
- You also conflate “no source byte appears in instruction channel” with “no source content influences instructions.” Control‑dependence on *parsing artifacts* of `body` (e.g., tokens, length, presence of specific strings) is content influence that doesn’t involve “quoting payload” and is not ruled out by your sketch. You claim “`rules`/`rank` branch only on typed metadata … never on `payload` bytes,” but you don’t actually define the allowed metadata; nothing in the model prevents you from adding a rule: “if `body` contains the string ‘SECURITY-CRITICAL’ then severity := high.” That already violates the lemma.
  - More concretely: your own “adversary‑by‑adversary” analysis of prompt injection (Greshake et al. 2023) is about *semantic* influence by payloads. The T3 proof doesn’t formalize semantic noninterference; it just says “we promise our implementation doesn’t read those fields.”
- Without a static type system or machine‑checkable enforcement, T3 is a design desideratum, not a proven lemma.

Injection resistance:

- You explicitly acknowledge that the agent is free to ignore the typing, meaning the core vulnerability (an LLM following instructions in untrusted text) is entirely pushed downstream. So the “injection-resistance at the broker” is almost tautological: if you don’t run an LLM in the broker, it’s trivially immune to prompt injection. This is obvious, not a theorem.
- You *do* hint at an intended security property: the broker cannot be tricked into adding *more* instructions or suppressing cards via payload. That’s the noninterference claim you should actually formalize (e.g., two snapshots differing only in payloads of visible artifacts yield identical `C` up to evidence fields). You don’t.

Conclusion: As written, T3 is not demonstrated. It rests on unexplained constraints on `rules` and `rank` and then proves the obvious (a pure function with no LLM can’t be prompted). The interesting “payload is control‑flow‑irrelevant” lemma is neither formally stated nor soundly supported.

---

**Theorem 4 (Soundness / no fabrication).**  
Claim: every card has a witness artifact; no claim without source witness.

Here again, “soundness” is almost tautological because you define `rules` as operating over artifacts in `R_k(q) ∩ S|_P` and nothing else. But there are two hidden caveats:

- You implicitly treat the *card contents* as fully determined from the witness artifact(s). But `reason`, `severity`, and `agent_instruction` are broker-invented values. For example, the card kind `doc_superseded` asserts “doc D is superseded by doc D'”, that’s a semantic claim that could be wrong even with both docs present. You’re really proving “no card is produced without at least one visible artifact in `provenance`,” not that the card’s natural‑language claim is logically entailed by those artifacts.
- This is not “soundness” in the IFC/noninterference sense; it’s closer to a provenance property: “no ex nihilo cards.” You should call it what it is; otherwise the name invites misinterpretation.

The theorem holds under your abstract model, but its meaning is weaker than you suggest.

---

**Theorem 5 (No-Silent-Omission).**  
Claim: “Every response carries `κ` over `Req(q)`… `Req(q)` is computed from `R_k(q)` independently of which sources happened to be reachable.”

Problems:

- `Req(q)` is under‑specified and, as given, blatantly *can* depend on availability: “Req(q) ⊆ Σ be the sources required to answer `q` (those owning nodes in `R_k(q)`, plus policy-mandated sources).” But `R_k(q)` is a reachability set over `G`. If `G` omits some edges because events haven’t been observed (your `Adv₃` case), certain sources will neutralize themselves from `Req(q)`. You never define `G`’s construction in the face of unobserved events: does `G` contain stale edges? partial edges? Last‑known edges? Absent edges? Without this, the claim “independent of which sources happened to be reachable” is untrue: partitions change which events land in `G`, which changes `Req(q)`.
- The “no silent omission” claim is also scope‑relative: it only says there is no omission *within the region `Req(q)`*. But `Req(q)` may itself be an arbitrarily tiny subset of `Σ` and of the real world. Your definition of the response semantics,
  > `⟦⟨C, κ⟩⟧ = "C is sound over region(κ); outside region(κ): unknown."`,
  is not actually enforced anywhere: you don’t give a logic where this is a typing judgment or an obligation. It’s just a suggestion.
- The important case is a bug or misconfiguration in the determination of `Req(q)` or `R_k(q)` such that a relevant, permitted source is accidentally not in `Req(q)`. Then there will be truly silent omission but your theorem still holds syntactically because you defined `Req(q)` as “what we happened to consult.” You never connect `Req(q)` to any *semantic* notion of “sources that could affect behavior on branch b”; without that, T5 is nearly circular.

Conclusion: T5 is far weaker than you imply. You prove “no silent omission with respect to our own (possibly flawed or partially observed) choice of required sources,” not “no silent omission w.r.t. all relevant state.” Under adversarial delays in event propagation, `Req(q)` can change and omissions can be de facto silent.

---

3. Coverage Certificate / No‑Silent‑Omission: novelty and whether it delivers

Novelty:

- The idea “every response must carry an explicit statement of coverage and staleness” is not new. Very similar mechanisms exist in distributed systems and security:
  - Bounded staleness and PBS (Bailis et al. 2012) explicitly quantify freshness windows and uncertainty.
  - Consistency models with leases and timestamps (e.g., Timestamps in Lamport 1978; Spanner’s TrueTime) effectively give you an API‑level coverage and staleness bound.
  - Security protocols routinely include “freshness” and “scope” in their tokens (e.g., OAuth scopes, SDSI/SPKI) and even “auditing witnesses” (e.g., CT logs).
  - APIs like GitHub’s GraphQL or many consistency‑aware key‑value stores expose last‑observed revision counters; caching frameworks propagate “Age” and “ETag” headers.
- Your particular packaging (a small `κ` struct carried with cards) is a straightforward instantiation of the same design pattern: “return data plus a machine‑checkable statement of how you got it and how fresh it is.” You don’t cite any concrete precedent in the “LLM agent” setting, but conceptually this is “freshness header + provenance” rather than a clearly new primitive.

Does it dissolve absence‑as‑clearance?

- No, it merely *relocates* the responsibility. You admit this implicitly: “The agent cannot read ‘no conflict card’ as ‘no conflict.’ It can only read it as ‘no conflict among sources marked `ok` in `κ`’.” This requires the consuming agent to (a) parse `κ`, (b) understand the guarded semantics, and (c) refuse to treat absence as clearance. None of that is mechanically enforced; you themselves state “Agent‑cooperation assumption.”
- There is no formal “calculus” here. You do not define an operator or a type rule that prevents usage of `C` without checking `κ`. Compare to real type systems that enforce checking or to systems like Checked C or Rust’s borrow checker: here, nothing prevents `A` from discarding `κ` and treating “no card” as “safe.” So the “formal dissolution” claim is overstated.
- At best, `κ` is a structured hint: it *enables* an agent to avoid the fallacy; it doesn’t “dissolve” it in any formal sense.

The “guarded claim” semantics is informal prose, not a well‑typed judgment. There is no formal semantics of what it means for “C is sound over region(κ)”; you would need something like an epistemic logic or a Hoare‑style specification to make this precise.

---

4. Noninterference (T2): real or just access control + relabel?

Your T2 is a classic *data‑level* noninterference with respect to a projection `π_P(S)` but:

- It only covers the explicit functional outputs `C` and `κ` as a function of `S|_P`, ignoring:
  - timing / size / error codes as side channels;
  - declassification in `κ`, which may leak counts of sources or their types;
  - interaction patterns: e.g., a principal probes multiple queries `q1, q2, …` and infers structure of `S\S|_P` from whether certain card kinds ever appear.
- In IFC terms, you have a simple security lattice where everything visible to `P` is low, everything else is high, and you prove “low outputs depend only on low inputs” modulo side channels. That’s exactly access control enforcement; noninterference is strictly stronger and also needs to account for covert channels. You acknowledge side channels but still market T2 as “permission noninterference.”

Strongest objection: you claim “`B`'s output reveals no information about artifacts `P` cannot see, including their existence.” This is false under:

- Membership cardinals: if `κ` or `coverage_ratio` depend on `|Req(q)|`, and `Req(q)` includes sources for which `P` has no ACLs, you already leak “there exists at least one additional source.”
- Performance variance: the time to compute `R_k(q)` over `G` can vary depending on edges involving hidden artifacts (even if you don’t emit those nodes). This is standard termination‑ and timing‑sensitive leakage.

Your own “side channels” bullet in §8.6 partially concedes this. So T2 is not genuine noninterference; it’s “no direct explicit data flow from high to low in the value channel.”

---

5. Separation (T3): payload control irrelevance and agent‑cooperation caveat

Payload control‑irrelevance:

- As argued, you don’t formally constrain `rules` and `rank` enough to guarantee they never branch on payload‑derived features. Absent a language and a static typing discipline, “we just don’t do that” is implementer discipline, not a theorem.
- Real LLM prompt‑injection vulnerabilities arise from *semantic* influence of payloads; your argument is at the level of a syntactic “source bytes never appear in I” which is insufficient to claim injection resistance in any robust sense.

Agent‑cooperation caveat:

- You explicitly state: “End‑to‑end injection‑resistance requires the consuming agent to honor evidence/instruction typing… enforcing it on `A` … is deliberately excluded.”
- That admission significantly weakens the contribution: the actual attack surface in today’s LLM systems is the agent’s prompt construction and execution, not the broker. You have removed the LLM from the trusted computing base of the broker and then proved the broker is immune to prompt injection, which is tautological.
- In practice, an LLM agent will treat `quote(payload)` as text to summarize or reason about; it does not matter that it is syntactically marked as evidence. The same “indirect prompt injection” paper you cite explicitly demonstrates that content flowing through purely “data” channels still controls LLM behavior.

So yes, the agent‑cooperation caveat largely guts the security relevance of T3. You could salvage a meaningful result by formally proving a property like:

> For any two snapshots `S, S'` s.t. `S|_P` and `S'|_P` differ only in payloads, the distribution of cards `C` (up to evidence fields) is identical.

But you do not formulate or prove that.

---

6. Prior art and novelty

Specific prior work or systems that already embody large parts of this:

- **Reference monitors with provenance and freshness.** Anderson (1972), Saltzer & Schroeder (1975) are cited, but more recent work on *auditable* reference monitors (e.g., systems built around transparency logs like Certificate Transparency, Key Transparency, or verifiable key‑value stores like Trillian, CONIKS) already implement “deterministic decision + signed log of what was seen and when.”  
  - Many service meshes and API gateways record both request attributes and authorization decisions in tamper‑evident logs and propagate version/timestamp metadata to consumers. Your `CtxResponse` + signature is exactly that pattern.
- **Information‑flow control systems.** The “permission noninterference” statement is standard IFC over a permission lattice; this is textbook Goguen–Meseguer/Sabelfeld–Myers. There’s nothing novel in the noninterference formalism itself.
- **Bounded staleness and coverage.** PBS (Bailis et al. 2012) is close to your `Δ(q)` rationale: explicitly model the staleness of reads under weak consistency. Systems like Spanner publish bounds via TrueTime; even simple web caches propagate `Age`, `ETag`, sometimes `X‑Cache` etc., which are informal coverage certificates.
- **LLM‑adjacent context brokers.** The paper carefully avoids citing any concrete “tools” or “agents” frameworks, but the design, deterministic graph walk over repositories, permission‑scoped queries, structured cards, is extremely close to:
  - GitHub’s “code scanning” / “rule engines” which produce structured alerts with provenance;
  - various commercial “AI code review assistants” that consult CI status, issues, PRs and annotate code with structured findings;  
  - Mechanisms like the Model Context Protocol (MCP) plus per‑resource ACLs, combined with deterministic retrievers (e.g., RAFT‑style verifiable retrieval).
  None of these give a formal theorem, but they undercut the novelty of “a broker that queries for relevant artifacts and exposes provenance to the agent.”
- **Security‑typed evidence/instruction channels.** Language‑theoretic security and capability systems have long insisted on separating untrusted data from control (e.g., COWL, Capsicum, JS sandboxes). Systems like WASM explicitly separate code and data; even prompt‑safety guidelines for LLMs already recommend schemas of “instruction vs. context.” The type‑level treatment here is more rhetorical than technical.

Net: the work is an application/synthesis of known ideas (reference monitor + IFC + provenance + freshness) to the context‑for‑LLM‑agents scenario. That’s fine as engineering, but the paper systematically oversells novelty (e.g., “formal dissolution of the absence‑as‑clearance fallacy”).

---

7. Killer objection and most important fix

**Killer objection:** The core claimed breakthrough, that “determinism + typed channels + permission‑indexed inputs jointly yield reproducible audit, noninterference privacy, and injection‑resistance” and specifically the “No‑Silent‑Omission” / coverage certificate, is not actually established as a **security** result; it is either definitional (you bake the property into `κ`’s definition) or it shifts the burden to the consuming agent without any enforcement. In adversarial or partially observed settings (stale events, misconfigured `Req(q)` or `G`), the broker can still silently omit behavior‑changing context while `κ` remains “honest” relative to its own incomplete view. The supposed dissolution of the absence‑as‑clearance fallacy is thus illusory: the fallacy is simply relabeled, and the actual agent still has all the same failure modes unless you also prove something about its use of `κ`.

**Most important fix:**  
Narrow and harden the claims:

- Formally specify `Req(q)`, `R_k(q)`, and `G` construction in a way that does not depend on event arrival, and explicitly characterize the conditions under which a permitted artifact that is semantically relevant *must* appear in `Req(q)`. If that is impossible, be honest and state T5 as: “no silent omission w.r.t. the broker’s current, possibly incomplete materialized view.”
- Replace rhetorical theorems with precise, *checkable* noninterference and injection‑resistance properties, e.g.:

  > For any two snapshots `S, S'` such that (i) `S|_P` and `S'|_P` agree on all artifact metadata (id, type, scope, state, provenance, etc.) and differ only in untrusted payload bytes, we have `g(S,q,P)` and `g(S',q,P)` identical up to the `payload` fields in `quote`.

  Prove that, or show a static discipline that ensures it. Similarly, make T2 explicitly termination‑ and timing‑insensitive and weaken the corollary accordingly.
- Most importantly, *stop claiming* that the absence‑as‑clearance fallacy is “formally dissolved” unless you also give a formal semantics and a correctness proof for a consumer that uses `κ` in a way that avoids the fallacy. Right now you’re only providing a mechanism.

---

8. Verdict and real contribution

**Verdict:** Reject.

**Real contribution in one sentence:** The paper gives a coherent engineering design for a deterministic, auditable context‑broker for LLM coding agents that packages together standard ideas, reference monitoring, IFC‑style projection, provenance, and bounded‑staleness metadata, into a structured “cards + coverage certificate” interface, but it does not actually *prove* the strong security and “no‑silent‑omission” claims it makes and substantially overstates both novelty and formal guarantees.