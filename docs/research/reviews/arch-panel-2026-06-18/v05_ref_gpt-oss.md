**Referee Report – teamctx v0.5 addendum**  
*Length: ≈ 660 words*  

The addendum introduces authority records, a richer “typed Unknown”, a certified‑set admissibility condition (T7), a vector‑based diagnostic classifier (T3″) and a restated observable‑soundness clause (E). The material is largely consistent with the earlier v0.3/v0.4 development, but several formal gaps undermine the claimed guarantees. I organise the comments by the numbered items in the request.

---

### 1. Authority state (Section A)

**Problem – circular/conflict definition.**  
`A(s) = conflicted` is defined as “≥ 2 priority‑maximal α∈applies(s) whose fresh typed values diverge”. The notion of “fresh typed value” is introduced only implicitly: it presumes the existence of a *typed* observation of `source(α)`. Yet the whole point of the authority layer is to avoid *value extraction* from the payload (the broker never emits a valuation). The definition therefore **requires** the same extraction that T7 is trying to restrict, i.e. a call to `φ_f(source(α))` for some field `f`. No syntactic restriction is given that the conflicting α’s must be *pinned* (as required by T7.2). Consequently the conflict detection is **underspecified**: a concrete implementation must either (i) perform an extraction that is outside the admissible set, violating T7, or (ii) rely on an external oracle that is not part of the formal model. This circularity is a genuine bug because the authority state cannot be computed from the *declared* data alone.

**Suggested fix.** Redefine `conflicted` to refer only to *metadata* that is already part of the declaration, e.g. “two maximal α with distinct `priority` fields” or “two maximal α whose *declared* values for a field differ”. If a value‑based conflict is needed, the rule must be explicitly tied to T7.2 (pinned, total `φ_f`). The paper should add a clause “conflicted ⇒ there exists a pinned field `f` such that …”, and prove that the extraction is admissible.

---

### 2. Leakage via `A(s)` in the coverage certificate (Section B)

The authors claim that emitting the categorical authority state does not reopen T2′/T6 because `A(s)` only ranges over *declared, P‑visible* sources. This argument is **insufficient**. The categorical value `conflicted` can only arise when at least two distinct declarations are simultaneously fresh. An adversary that controls the timing of a declaration (e.g. by publishing a new `α` with higher priority) can cause the broker to flip `A(s)` from `resolved` to `conflicted`. Observing this flip leaks the *existence* of a newly‑added declaration, even if the declaration’s payload is invisible to the consumer. This is a classic *existence‑privacy* channel: the observable `κ` now depends on the *set* of declarations, not merely on their *type*.

Formally, the leakage bound T6 (single‑shot mutual‑information ≤ δ) was proved under the assumption that the observable is a deterministic function of the *valuation* `⟦·⟧` (which never includes authority). Adding `A(s)` as an extra argument to `κ` changes the observable’s domain, and the original proof does not cover it. The authors must either (a) prove a new bound that accounts for the entropy of the declaration set, or (b) restrict `κ` to output only `resolved`/`missing`/`temporary` (i.e. collapse `conflicted` to `Unknown[unobserved]`). Until such a proof is supplied, the claim that T2′/T6 remain intact is **invalid**.

---

### 3. Certified‑set admissibility (Section C / T7)

**Soundness vs. completeness.**  
The admissibility rule is *sound* in the sense that any claim admitted to `C` must be either extraction‑free or pinned‑typed with a declared authority. However, the rule is **not complete**: it excludes many useful claims that could be safely admitted (e.g. deterministic comparisons over *enumerated* values that are not formally “typed” but are still bounded). The current formulation forces a *binary* decision on every field, which is unnecessarily restrictive.

**Achievability of “total, validated” extractors.**  
The paper asserts that a total, validated extractor `φ_f` exists for any pinned field. No construction is given, nor any discussion of how validation is performed. In practice, totality fails for optional fields, versioned schemas, or forward‑compatible extensions. Without a mechanised proof that the extractor respects the declared schema *and* is total, the admissibility clause is hand‑waved. Moreover, the experiment that measured a precision of 0.44 is **mis‑used**: a precision figure is a *statistical* property of a particular detector, not a *semantic* guarantee for a protocol. Embedding that number into a formal admissibility predicate conflates empirical evaluation with logical soundness, which is a category error. The protocol should instead state a *requirement* (“extractor must be proven correct w.r.t. the schema”) and leave the empirical measurement as a *design justification* outside the formal core.

**Suggested fix.** Separate the *formal* admissibility condition (which must be provable) from the *empirical* motivation. Provide a definition of “validated extractor” (e.g. a certified program with a proof of functional correctness) and, if desired, cite the experiment only as a motivation for restricting to pinned fields.

---

### 4. Vector classification and injection‑resistance (Section D / T3″)

The claim that T3″ inherits the injection‑resistance of T3′ rests on the premise that each judge `j_i` is *feature‑mediated* and therefore cannot be influenced by payload‑level code execution. However, the definition of a judge is **too abstract**: `j_i ∈ {1,0,⊥}` is a *value* that may be produced by any deterministic function of the payload. An adversary can embed a crafted payload that triggers a different branch in the extractor, causing `j_i` to flip from `0` to `1`. Since the classifier `class` is a pure function of the vector, the whole classification can be altered without violating determinism. The original injection‑resistance proof for T3′ relied on the *absence* of any payload‑directed control flow; this guarantee does not automatically extend to a composition of multiple judges.

To preserve injection‑resistance, the paper must **prove** that each `j_i` is *independent* of the payload’s syntactic structure, i.e. that the extraction pipeline is *pure* with respect to the payload. A sketch argument (“composition of feature‑mediated judgments is feature‑mediated”) is insufficient; a formal non‑interference lemma is required. Until such a lemma is added, the claim is **unsubstantiated**.

---

### 5. Restated observable soundness (Section E)

The restatement is broadly compatible with v0.3, but the phrase “demoted, not suppressed” is **underspecified**. The protocol defines a *volume gate* that suppresses cards whose value agrees with the resolved authority, yet it does not formalise the *demotion* operation (e.g. whether the card is moved to `H`, to a lower‑priority `C`, or simply annotated). Moreover, the soundness theorem in v0.3 required a precise relationship between the consumer’s under‑approximation `⟦·⟧⁻` and the broker’s emitted certificate. The new clause adds a conditional “non‑authoritative dissent is demoted” without stating the corresponding rule for `⟦·⟧⁻`. Consequently the proof obligations for observable soundness are incomplete. The authors should extend the formal definition of the consumer rule to include a demotion case and show that the resulting under‑approximation still satisfies the original soundness inequality.

---

### 6. Overall consistency

The addendum introduces **new circular dependencies** (authority ↔ extraction) and **new observable channels** (authority state) that were absent in v0.3/v0.4. These changes break the original non‑interference argument and the single‑shot leakage bound. Moreover, the sharpening of A4 (φ‑robustness) creates a *partial* assumption that is not reflected in the earlier proofs, which treated φ as globally reliable. The paper therefore contains an **internal inconsistency**: the same assumption is both weakened (only for pinned fields) and used unchanged in the proofs of T3′ and T5′.

---

## Verdict

**Major‑Revision**  

The contribution is promising, authority records and vector classification are natural extensions, but the current manuscript contains several formal defects that prevent acceptance in its present form. To reach a publishable state the authors must:

1. **Redefine `conflicted`** so that its detection does not rely on inadmissible extraction, or explicitly tie it to T7.2 with a formal proof of admissibility.  
2. **Provide a leakage analysis** for the categorical `A(s)` emitted in `κ`, either showing that the mutual‑information bound still holds or redesigning `κ` to hide conflict information.  
3. **Separate empirical motivation from formal admissibility**, and give a concrete definition (and ideally a mechanised proof) of “total, validated” extractors.  
4. **Supply a non‑interference lemma** for the vector‑classification pipeline, demonstrating that each judge is truly feature‑mediated.  
5. **Formalise the demotion operation** and extend the consumer under‑approximation rule accordingly, completing the observable‑soundness proof.  
6. **Audit all proofs** that previously used A4 to ensure they remain valid under the narrowed assumption.

Addressing these points will restore the rigorous foundations that the earlier versions established and will make the v0.5 addendum a solid, formally verified extension.