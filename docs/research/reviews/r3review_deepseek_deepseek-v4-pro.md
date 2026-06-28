**Round‑2 defect fixes (v0.3)**

- **F1 (T6 definitional collapse), RESOLVED.** The split into `rel_G` (over the unpermissioned graph `G`) and `rel_render` (over the observed subgraph `Ĝ_P`) correctly makes the existence of a globally‑relevant `P`‑invisible source non‑vacuous, and T6 now quantifies over `rel_G`.
- **F2 (§5.6 `False` unsoundness), RESOLVED.** `False` is now guarded by completeness over the global dependency set `deps_G(ρ)`, with disconnected/unavailable sources forcing `Unknown`. The addition of `witness` and `deps_G` maps is a step toward evaluability, though see the new defect below.
- **F3 (T3′ overclaim), RESOLVED.** The theorem has been downgraded to **feature‑mediated selection**, with the precise statement that adversarial text can shift an artifact between `Φ`-classes but cannot inject free‑form control/instructions. The `φ`‑robustness assumption (A4) and its limitation are explicitly owned.
- **F4 (T5′ naming / ceiling), RESOLVED.** Renamed “Foreign‑Key‑Based Observable Soundness”; the theorem now explicitly confines omissions to “relevance not encoded as a typed reference and not policy‑mandated,” so the ceiling is part of the claim, not hidden in limitations.
- **F5 (T6 triviality), RESOLVED.** The impossibility is properly positioned among declassification, hyperproperties, polyinstantiation, and query‑completeness. The quantitative `δ`‑leakage bound (0 / ≤log₂(N+1) / full bits) adds a modest but genuine refinement, moving T6 from tautology to a characterised frontier.

**New defect introduced by v0.3**

- **§5.6 semantics remains under‑specified and not fully evaluable.** The guarded semantics relies on the maps `witness : C → 2^Prop` and `deps_G : Prop → 2^Σ`, but neither map is concretely defined. In particular, `deps_G` is described only informally as “the **global** sources whose state can affect ρ (over `G`, not `Ĝ_P`)”. Without a constructive definition (e.g., from typed references, policy, and the query structure), the semantics is not executable, and the claim that “`False` requires provable completeness over the global dependency set” remains hollow. Furthermore, the consumer is expected to use `deps_G` to interpret `Unknown`, but the paper does not specify how `deps_G` is computed, transmitted, or kept sound within the trust boundaries. This gap undermines the otherwise careful formal treatment and should be closed.

**Contribution**

The core contribution is defensible for a workshop or conference that accepts strong conceptual / systems‑security papers: a formalisation of context retrieval for acting agents as deterministic mediation with an explicit, quantified privacy–coverage impossibility and foreign‑key‑based observable soundness, together with a declassification dial. The work is synthetic rather than providing a full implementation, but the characterisation of the tradeoff is novel and well‑scoped.

**Updated verdict**

**Minor revision.** The single remaining blocker is the need to define `deps_G` and `witness` concretely within the formal model (§3), explain how `deps_G` is communicated to the consumer, and ensure that the three‑valued semantics is genuinely evaluable under the stated assumptions (notably A1). Once these definitions are precise, the paper will be ready for acceptance.