# teamctx Protocol — v0.4 revision addendum (applied on v0.3)
*Surgical revision closing the two convergent blockers from the round-3 (v0.3) panel, which returned unanimous **minor revision**. This addendum rewrites §5.6 and Theorem 6 and adds four clarifying sentences. All other sections of v0.3 carry over unchanged.*

---

## Response to Reviewers (round 3)

- **[B1 — Gemini/DeepSeek] §5.6 epistemic contradiction + non-constructive `deps_G`.** *Fixed.* `⟦·⟧` is now explicitly **meta-theoretic** (an omniscient-oracle analysis used to prove that omissions default to `Unknown`); the broker never computes or emits it at runtime, so the `False→Unknown` shift cannot become a value-channel leak (T2′ preserved). The **consumer** computes only a sound under-approximation from `⟨C,κ⟩`. `deps_G` is given a constructive, conservative (over-approximating) definition and is named as a trusted-rule obligation.
- **[B2 — GPT-5.1/gpt-oss] T6 δ-leakage not an info-theoretic statement.** *Fixed.* The bound is now a precise **single-shot mutual-information** statement with an explicit adversary model and out-of-scope clauses (multi-query, non-value channels).
- **Minor (non-blocking) asks** acknowledged with clarifying sentences (A2 sequencer instantiation; hint-layer security bound; `φ`-robustness as conditional; mechanized proof as future work).

---

## §5.6 (REPLACEMENT) — Guarded semantics, as meta-theory + a sound consumer rule

**Constructive dependencies.** For a proposition `ρ` over work-state, define `deps_G(ρ) ⊆ Σ` as the sources whose state can affect `ρ`, computed as a **conservative over-approximation** from: (i) the typed references reachable from `ρ`'s subject in the *global* graph `G`, (ii) `policy_mandated` sources for `ρ`'s scope, and (iii) the query structure. `deps_G` is part of the trusted rule set; **soundness of `False` requires `deps_G` to over-approximate the true dependency set** (stated as an obligation, not assumed for free). `witness : C → 2^Prop` maps each card to the propositions it establishes (fixed per card kind).

**Meta-theoretic valuation (oracle view).** Define `⟦·⟧ : Prop → {True, False, Unknown}` *relative to an omniscient oracle over `G`*, used only to state and prove soundness:
- `⟦ρ⟧ = True` if `∃ c∈C. ρ∈witness(c)`;
- `⟦ρ⟧ = False` iff `∀ σ∈deps_G(ρ): (σ∈κ ∧ status(σ)=ok)` and no witness exists;
- `⟦ρ⟧ = Unknown` otherwise.

**The broker emits no valuation.** `B`'s only output is `⟨C, κ⟩`. It does **not** compute or transmit `⟦ρ⟧`. (This is the fix for B1: were `B` to emit `⟦ρ⟧` at runtime, adding a `P`-invisible source to `deps_G(ρ)` would flip `False→Unknown`, a value-channel signal of invisible existence that would violate T2′. By keeping `⟦·⟧` meta-theoretic, T2′ is preserved.)

**Sound consumer rule (runtime, under-approximating).** A consumer holding only `Ĝ_P` and `κ` evaluates a *safe refinement* `⟦·⟧⁻`:
- assert `True` exactly when a card witnesses `ρ`;
- assert `False` **only if** `deps_G(ρ)` is fully present in `κ` with `status=ok` *and* the consumer can verify `deps_G(ρ)` is complete for `ρ` (typically only when `ρ`'s dependencies are all typed-referenced and policy-bounded — A1);
- otherwise `Unknown`.

**Soundness lemma.** `⟦ρ⟧⁻ = True ⇒ ⟦ρ⟧ = True`, `⟦ρ⟧⁻ = False ⇒ ⟦ρ⟧ = False`; the consumer never over-claims (it may only *under*-claim, returning `Unknown` where the oracle would say `False`). *Sketch:* `⟦·⟧⁻` strengthens the `False` precondition with a verifiable-completeness check; `True` is identical; all other cases collapse to `Unknown`. ∎ Because the relevance ceiling (T5′/A1) usually blocks the completeness check, `Unknown` is the conservative default — the intended honest behavior. The consumer obligation remains `treat Unknown ≠ False`.

---

## Theorem 6 (REPLACEMENT) — Privacy–Coverage Impossibility with single-shot leakage bound

**Qualitative (unchanged).** Define **EP**: `g` invariant under changes confined to `P`-invisible artifacts; **CC**: for every globally-relevant (`rel_G`) unobserved source `σ`, `κ` reports `σ`'s existence. *If a globally-relevant `P`-invisible source can exist, EP and CC are jointly unsatisfiable.* (Proof as in v0.3: construct `S` with such a `σ`, `S′=S∖{σ}`; invisibility ⇒ `S|_P=S′|_P`; CC ⇒ outputs differ ⇒ EP fails. ∎) This is the noninterference-vs-completeness/declassification tension (Sabelfeld–Myers; Clarkson–Schneider; Jajodia–Sandhu; Motro) **specialized to agent context**; the qualitative result is not claimed as novel.

**Quantitative (single-shot leakage — the precise statement, fixing B2).** *Adversary model:* a single invocation; the secret is the presence vector `X ∈ {0,1}^M` over a fixed, adversary-known candidate set of `M` potential invisible-target dangling references; the adversary has an arbitrary prior on `X`; the only observable is `δ(D(q))`; timing, cardinality-of-`C`, and cross-call correlation are **excluded** (A2 + §8 side-channel scope). Let `N = |D_inv(q)|` be the number of *present* invisible-target dangling refs, `N ≤ M`. Then the mutual information between `X` and the observable is:
- **`δ=none`:** the observable is independent of `X` ⇒ `I(X; obs) = 0` bits.
- **`δ=count`:** the observable is exactly `N ∈ {0,…,M}` ⇒ `I(X; obs) ≤ H(N) ≤ log₂(M+1)` bits.
- **`δ=identity`:** the observable is `X` restricted to present refs ⇒ `I(X; obs) ≤ M` bits.
*Sketch:* data-processing on the (deterministic) map `X ↦ obs`; `H(f(X)) ≤ log₂|range(f)|`; `|range| = 1, M+1, ≤2^M` respectively. ∎

**Scope (honest).** This bounds *single-shot value-channel* leakage only. Adaptive multi-query leakage (correlated `D(q)` across requests), timing, and certificate-size channels are **open problems**, not covered. The contribution of T6 is therefore the *framing + single-shot characterization*, not a complete information-theoretic treatment.

---

## Four clarifying sentences (non-blocking asks)

1. **A2 instantiation.** Concretely, the single logical sequencer is the broker's append-only ingestion log (monotonic per-broker sequence numbers); multi-region deployments require a CRDT fold (commutative/associative/idempotent), which is out of scope.
2. **Hint-layer bound (§6).** The untrusted client-side hint layer (including any recovery of implicit/free-text references) is **never admitted to `C`** and carries **no certificate weight**; its outputs are presented to the consumer as explicitly untrusted and cannot inflate any observable-soundness claim.
3. **`φ`-robustness (A4).** The injection-resistance corollary of T3′ is **conditional on A4**; robust typed feature extraction against adversarial formatting is an empirical open problem, not proven here.
4. **Proofs.** This is a working paper with proof *sketches*; a mechanized artifact (e.g., Coq/Isabelle for the determinism, noninterference, and guarded-semantics soundness lemmas) is future work.
