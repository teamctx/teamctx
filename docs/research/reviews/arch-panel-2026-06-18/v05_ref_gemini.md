**Review Report: teamctx Protocol v0.5 Addendum**
**Verdict: MAJOR REVISION**

The v0.5 addendum introduces necessary pragmatic constraints (authority, phantom suppression) to the formal model. However, it introduces a critical privacy leak in the guarded semantics (§B), a formal contradiction regarding observable soundness (§E vs. §C), and relies on an impossible assumption of totality for extractors. 

Below is the section-by-section analysis.

### 1. §A: Authority State (Underspecified / Circularity)
**Objection:** The definition of `conflicted` is underspecified and implicitly circular. It requires evaluating if "fresh typed values diverge." To evaluate divergence, the broker must extract values using $\phi$. If this extraction occurs *before* the T7 restriction is applied, it inherits the exact 0.44-precision unreliability T7 seeks to ban. Furthermore, what happens if extraction fails? 
**Fix:** $A(s)$ must be explicitly defined over the *pinned-typed extractor* $\phi_f$ defined in T7.2. Additionally, the definition must formally handle extraction failure ($\bot$): does $\bot$ diverge from a valid value $v$, or does it yield `Unknown[unobserved]`?

### 2. §B: Guarded Semantics (T2'/T6 Privacy Leak)
**Objection:** The claim that emitting the categorical $A(s)$ in $\kappa$ "does not reopen T2' (existence-privacy)" is **false**. The text asserts $A(s)$ ranges "only over declared, P-visible sources." But $\Delta$ is defined as a globally supplied manifest (e.g., checked-in `.teamctx`). If $\Delta$ contains a priority-maximal rule pointing to a source $S_{secret}$ that consumer $P$ cannot read, emitting `Unknown[conflict]` or `Unknown[unobserved]` directly leaks the existence, freshness, and value-divergence of $S_{secret}$ relative to visible sources.
**Fix:** The broker must compute a consumer-specific projection $\Delta_P = \{ \alpha \in \Delta \mid \text{can\_read}(P, \text{source}(\alpha)) \}$. $A(s)$ must be computed strictly over $\Delta_P$, not $\Delta$.

### 3. §C: Certified-Set Restriction T7 (Formal Fiction)
**Objection:** Grounding a formal rule in empirical measurement (0.44 precision) is not a category error, it is a valid justification for introducing an axiomatic restriction. However, the requirement for a "**total**, validated extractor" $\phi_f$ is a formal fiction. No real-world parser over external artifacts is total; malformed payloads exist. 
**Fix:** $\phi_f$ must be modeled as a partial function or explicitly return an error state ($V \cup \{\bot\}$). T7.2 must then rigorously define the admissibility of comparisons involving $\bot$ (e.g., $\bot \neq v$ is a structural failure, not a typed value disagreement).

### 4. §D: Diagnostic-Vector T3'' (Injection vs. Evasion)
**Objection:** The section is formally sound but risks conflating injection with evasion. Because $class$ is a fixed total function over $J(c)$, it strictly preserves T3' non-interference (payload is never evaluated as an instruction). However, an adversary *can* craft a payload to deterministically flip a feature (e.g., altering whitespace to flip $j_{semequiv}$ from 1 to 0), thereby forcing the classifier to output `suppress`. 
**Verdict:** Sound. The protocol correctly prevents *injection* (arbitrary state execution), and the "robustness caveat" correctly acknowledges that *evasion* (adversarial feature-flipping) is possible where judges rely on free text. No fix required, but the distinction must be maintained in proofs.

### 5. §E: Authority Soundness (Fatal Contradiction with T7)
**Objection:** There is a direct contradiction between §E and §C (T7). §E states that "non-authoritative dissent... is demoted, not suppressed" and that suppressing it "would violate observable soundness." To preserve observable soundness, this dissent must live in the certified set $C$. However, T7 explicitly states that *only* comparisons licensed by a declared authority $\alpha \in \Delta$ are admissible to $C$, and "all other value-disagreement claims... are not admissible to C." A non-authoritative dissent is, by definition, a comparison involving a non-$\alpha$ source. 
**Fix:** You cannot have it both ways. Either:
1. Carve out a formal exception in T7.2 allowing pinned-typed comparisons between *any* source and the resolved authority $\alpha$.
2. Accept that non-authoritative dissent goes to the untrusted hint layer $H$, and formally weaken observable soundness to apply *only* to authoritative declarations (which aligns with the "authority-relative soundness" goal).

### 6. Overall Consistency
The transition from a blanket A4 assumption to a scoped, testable A4 (via T7) is a massive improvement for the protocol's rigor. However, the v0.5 addendum cannot be accepted until the T2' privacy leak in $\Delta$ resolution (§B) and the T7 vs. §E contradiction are resolved. 

**Required Actions for Acceptance:**
1. Define $\Delta_P$ to patch the T2' leakage channel.
2. Replace the "total" $\phi_f$ requirement with rigorous $\bot$-handling.
3. Resolve the contradiction between T7 admissibility and §E non-authoritative dissent.