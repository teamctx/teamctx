**1. B1 RESOLVED.** Shifting the 3-valued semantics to the meta-theory cleanly eliminates the value-channel leak (preserving T2′), while the constructive over-approximation of `deps_G` and the consumer-side under-approximation rule provide a practical, sound mechanism for handling `Unknown` without epistemic contradictions.

**2. B2 RESOLVED.** The revision replaces the informal leakage assertion with a rigorous single-shot mutual information bound ($I(X; obs)$), explicitly defining the adversary model and correctly scoping out adaptive/multi-query and side-channel complexities.

**3. REMAINING BLOCKERS:** None. The authors have systematically closed every structural and theoretical gap identified in previous rounds. The surgical v0.4 addendum does exactly what was required without introducing new moving parts.

**4. FINAL VERDICT:** **Accept.**

***

### Frontier Reviewer Evaluation

The authors have executed a textbook surgical revision. In v0.3, the paper presented a compelling architecture for certified context mediation but tripped over its own formalism in two critical places: an epistemic contradiction in the guarded semantics that inadvertently broke its own noninterference theorem, and an informal leakage bound that lacked information-theoretic rigor. 

The v0.4 addendum addresses both blockers with absolute precision.

**On B1 (Epistemic Contradiction & Semantics):** 
By moving the `⟦·⟧` valuation to the meta-theory (the "oracle view"), the authors correctly recognize that the broker cannot compute `False` without violating existence-privacy (T2′). The broker now strictly emits the certificate `⟨C, κ⟩`, leaving the epistemological burden to the consumer. The introduction of the consumer-evaluated safe refinement `⟦·⟧⁻` is an elegant and highly practical solution: it allows the consumer to assert `False` only when completeness is verifiable (which is rare, as the authors note), safely defaulting to `Unknown` otherwise. Furthermore, defining `deps_G` as a constructive, conservative over-approximation based on typed references and policy mandates transforms it from a magical oracle into a concrete trusted-rule obligation. The semantics are now evaluable, sound, and non-leaky.

**On B2 (Theorem 6 Leakage Bound):** 
The formalization of Theorem 6 is now mathematically sound. By defining the secret as a presence vector $X \in \{0,1\}^M$ over candidate invisible-target dangling references, and bounding the single-shot mutual information $I(X; obs)$, the authors provide a rigorous foundation for their declassification dial. The bounds—0 bits for `none`, $\le \log_2(M+1)$ bits for `count`, and $\le M$ bits for `identity`—are correct and well-justified by standard data-processing inequalities. Crucially, the authors explicitly scope out adaptive multi-query leakage, timing, and certificate-size channels. This intellectual honesty strengthens the paper; it bounds what is solved today while clearly marking the frontier for future cryptographic or information-theoretic work.

**On Minor Asks:** 
The inclusion of the four clarifying sentences addresses the minor panel requests perfectly. Explicitly stating that the hint layer carries no certificate weight, acknowledging that A4 (`φ`-robustness) is an empirical open problem rather than a proven guarantee, and deferring mechanized proofs to future work all serve to perfectly calibrate the paper's claims. 

**Broader Impact:**
With the theoretical foundation now solidified, this paper stands as a definitive reference point for agent-context systems. The industry is currently flooded with RAG-based approaches that dangerously conflate recall with truth, and absence with safety. This paper provides the formal vocabulary—*Foreign-Key-Based Observable Soundness*, *Feature-Mediated Selection*, and the *Privacy–Coverage Impossibility*—to explain exactly why those approaches are structurally insufficient for acting agents, and what must be built instead. The framing of context as "certified mediation under partial observability" is a necessary paradigm shift for the security of autonomous systems.

Congratulations to the authors on a tight, rigorous, and highly readable paper. Ready for publication.