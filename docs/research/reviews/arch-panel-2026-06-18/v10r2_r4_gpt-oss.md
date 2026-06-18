**Round‑2 Review – Formal‑Methods Referee**

Below is a two‑part assessment of the revised protocol.  I treat each of the five “fixes” from Round 1, then examine the new interactions they create.  The tone is deliberately strict: I only point out genuine gaps, not imagined ones, and I keep the discussion within the formal model that the paper defines.

---

### PART 1 – Did the fixes close the original defects, or merely paper‑over them?

| # | Fix | What the revision claims | Formal status |
|---|------|--------------------------|---------------|
| (i) | **O1 as an “assumption‑with‑enforced‑discharge”** | The broker now validates each connector’s schema manifest at deployment; any emitted reference class that is not declared causes `incomplete[unmodeled‑ref]`. The global over‑approximation of `deps_G(ρ)` is still an *assumption* (the “honest trusted‑base” hypothesis). | **Closed, but not eliminated.**  The validation step makes the assumption *observable*: a deployment that violates O1 is rejected, so the hypothesis is never silently broken.  However, O1 remains an *axiom* about the composition of local completeness into a global over‑approximation; the paper does not provide a proof that the composition is sound.  The fix therefore eliminates the *implementation* loophole but does not remove the logical assumption. |
| (ii) | **Unbounded syntactic check → total `complete?`** | `complete?` is now a total function returning either `complete` or an `incomplete[reason]`. The “unbounded” reason is produced by a purely syntactic, depth‑bounded traversal (or a schema flag) and never by a semantic finiteness test. | **Closed.**  The definition is now mathematically total: every pair `(Prop,κ)` yields a value, and the set of reasons is exhaustive (`dangling`, `stale‑dep`, `policy‑gap`, `unbounded`, `unmodeled‑ref`).  No hidden partiality remains. |
| (iii) | **δ‑gated closure status** | The broker computes `complete?` over the consumer projection `Δ_P` and then filters the resulting reason through the declassification dial `δ`.  Invisible‑target gaps are collapsed to a generic `Unknown[unobserved]`. | **Closed, but with a new privacy‑soundness trade‑off.**  The masking is explicit and respects the privacy policy: the consumer never learns that a particular invisible target is dangling.  The formal guarantee that “cannot reopen T5/T6” follows directly from the definition of the mask.  The only remaining question is whether the consumer’s *soundness* proof (Theorem 2) still holds when the reason is hidden; the paper argues it does because the consumer rule `⟦·⟧⁻` never inspects the reason. |
| (iv) | **Polarity / “False‑by‑counterexample”** | `⟦ρ⟧ = False` either when a counterexample card witnesses `¬ρ` **or** when `complete?(ρ,κ) = complete` and no positive witness exists.  The “counterexample” route is justified by Theorem 3 (witnesses are never fabricated). | **Closed, but not fully justified for all proposition shapes.**  The rule works for *existential* propositions (a single witness suffices) and for *universal* propositions (a single counterexample suffices).  The paper does not discuss mixed or higher‑order propositions (e.g., `∀x.∃y. P(x,y)`).  In those cases the current definition of “counterexample” is ambiguous, so the fix is only partial. |
| (v) | **`Unknown[stale‑authority]`** | Authority status now distinguishes a fresh maximal source that is *stale* (observed but outdated) from a completely missing source.  The stale case is never silently overridden by a lower‑priority fresh source. | **Closed.**  The addition is a clean extension of the authority lattice; the definition is total and the distinction is used consistently in §8 and the worked example.  No previous theorem is broken by this extra case. |

**Summary of Part 1:** All five defects are addressed at the level of the specification.  The only lingering “paper‑over” is the reliance on O1 as an unchecked axiom about global completeness; the enforcement step makes it *observable* but does not eliminate the need for an external trust assumption.  The polarity rule is still incomplete for complex logical forms.

---

### PART 2 – New contradictions introduced by the fixes

#### (a) Polarity: Can a card set `C` contain both a witness of `ρ` and a witness of `¬ρ`?

The model treats `C` as a multiset of *certified cards* that each *witness* a proposition.  Nothing in the revised text forbids two distinct cards, one for `ρ` and one for `¬ρ`, from co‑existing.  The semantics of `⟦·⟧` resolve this as follows:

* If a card for `ρ` exists, `⟦ρ⟧ = True` (the rule is “existential”).  
* If a card for `¬ρ` exists, `⟦ρ⟧ = False` (the “counterexample” rule).

Thus a simultaneous presence would make `⟦ρ⟧` both `True` and `False`, an outright inconsistency.  The paper’s intended mitigation is to route *source‑level* conflicts to the *authority* layer (the “conflicted” case in §8).  However, the current text does **not** state that a counterexample card is generated *instead of* a conflicting authority entry; the two mechanisms are orthogonal.  Consequently, the protocol as written permits an illegal state where `C` contains contradictory cards, breaking the invariant that `⟦·⟧⁻` is a *partial* function.  A missing clause such as “if both a witness and a counterexample exist, treat the situation as an authority conflict and discard the valuation” is required.

#### (b) δ‑gating: Does masking invisible‑target gaps weaken consumer soundness?

Consumer soundness (Theorem 2) relies on the fact that the consumer rule `⟦·⟧⁻` never distinguishes *why* a dependency is incomplete; it only cares whether the dependency is *complete* or not.  The δ‑gate therefore seems harmless.  The subtlety is that the broker still emits the *count* of dangling references (the paper says “any count withheld” for `δ = none`).  If the consumer can observe the *absence* of a count, it may infer that the gap is invisible‑target rather than visible‑target, thereby leaking a binary fact about the policy.  The current definition of `Unknown[unobserved]` does **not** guarantee that the count is always omitted; the text only mentions “the [dangling] reason and any count withheld”.  To preserve privacy, the implementation must also hide the *cardinality* of the set of invisible‑target gaps.  As written, the protocol leaves this detail unspecified, creating a potential side‑channel that could be exploited to distinguish the two cases, and thus marginally weakening the consumer‑soundness guarantee.

#### (c) Counterexample‑False route and T5/T6 (existence‑privacy)

T5/T6 guarantee that a consumer cannot learn about *invisible* dangling references unless the declassification dial `δ` is raised.  Counterexample cards are, by definition, *P‑visible* (they must be emitted to the consumer).  The revised §5 explicitly states that a counterexample card “witnesses `π`” and is part of the broker’s output `⟨C,κ⟩`.  Since `C` is already filtered by `Δ_P`, a counterexample cannot refer to an invisible target.  Therefore the counterexample route does **not** bypass the privacy guarantees: the consumer never receives a card that would expose an invisible dangling reference.  The only way a privacy breach could occur is if the broker mistakenly classifies an invisible‑target counterexample as visible, which would be a bug in the `Δ_P` projection rather than a logical flaw in the theorem.

#### (d) Deployment‑time manifest validation (O1 enforcement)

The paper now says: “broker validates each connector’s schema manifest at deployment; any class a connector emits but did not declare makes `complete?` return `incomplete[unmodeled‑ref]`”.  This is a concrete operational step, but the description is still high‑level: it does not specify *how* the broker inspects runtime emissions to guarantee that no undeclared class ever appears.  In a deterministic, read‑only context broker, the only way to enforce this is to perform a *static* analysis of the connector’s code or to sandbox the connector and inspect all outgoing messages.  The revision does not discuss the feasibility of such static analysis (e.g., handling dynamic language features) nor does it provide a proof that the validation is *complete* (i.e., that no undeclared class can slip through a runtime bug).  Consequently, the enforcement clause is still an *implementation assumption* rather than a formal guarantee.  It does not invalidate the theorems, but it weakens the claim that O1 is “enforced” in a mathematically rigorous sense.

#### (e) Impact on prior theorems T1–T8

| Theorem | Effect of the fixes |
|--------|----------------------|
| **T1 (observable soundness)** | Unchanged; `⟦·⟧⁻` still mirrors the broker’s semantics. |
| **T2 (False routes)** | The new “counterexample” rule adds a second way to derive `False`.  The original proof of T2 only covered the “exhaustive‑absence” case.  The proof must be extended to show that a counterexample card is always trustworthy (Theorem 3 already does this, but the paper does not explicitly link T2 to Theorem 3). |
| **T3 (witness non‑fabricated)** | Still holds; the counterexample route relies on Theorem 3, so no regression. |
| **T4 (coverage certificate correctness)** | Unaffected; `complete?` remains total. |
| **T5/T6 (existence‑privacy with δ)** | The δ‑gate is now explicitly defined, so the theorems remain valid provided the masking of counts (see (b)) is enforced. |
| **T7/T8 (feature‑mediated injection resistance & authority model)** | The introduction of `Unknown[stale‑authority]` fits cleanly into the authority lattice; T8’s invariants are preserved.  The only missing piece is the authority‑conflict handling of contradictory cards (see (a)). |

Overall, the theorems survive, but the paper must add a short lemma that “counterexample cards are a subset of P‑visible cards” and a clause that “if both a witness and a counterexample for the same proposition appear, the situation is escalated to an authority conflict and the valuation is discarded”.

---

### Verdict

**Decision: Accept‑with‑nits (minor revision).**  

The revised protocol successfully closes the five defects identified in Round 1.  The remaining concerns are:

1. **Explicit handling of contradictory cards** – add a rule that such a situation is treated as an authority conflict rather than a logical inconsistency.
2. **Complete privacy of the δ‑gate** – guarantee that the cardinality of invisible‑target gaps is also hidden.
3. **Clarify the deployment‑time manifest validation** – either provide a sketch of a static analysis technique or acknowledge the enforcement as an implementation assumption.
4. **Extend the proof of T2** to cover the new counterexample‑based `False` route, and cite Theorem 3 accordingly.
5. **State the restriction on proposition shapes** (existential/universal) or broaden the definition of “counterexample” to higher‑order formulas.

Addressing these points will make the formal development fully self‑contained and eliminate the minor logical gaps identified above.  Once the authors incorporate the suggested clarifications, the paper can be accepted without further revision.