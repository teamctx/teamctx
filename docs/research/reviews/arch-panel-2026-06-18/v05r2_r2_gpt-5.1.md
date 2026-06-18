PART 1 – Status of the six round‑1 issues

I’ll take them in order.

**(A) Authority “conflicted” & banned extraction**

Previously: authority relied on open-ended extraction that T7 was simultaneously banning.

Now: authority is rigidly scoped to pinned, typed extractors `φ_f` that are (i) declared on a schema field `f`, (ii) partial (`V ∪ {⊥}`), and (iii) must be T7.2‑eligible/validated. Open-ended extractors are explicitly *not* used by authority.

This removes the circular dependence on an inadmissible extractor. The “conflicted” state can only arise from validated `φ_f` on declared fields. That is a genuine fix, not wording.

**Conclusion (A): closed.**

---

**(B) Authority state leaking existence of invisible declarations**

Previously: `A(s)` was computed over all of `Δ`, so flips in `A(s)` could reveal presence of consumer‑invisible declarations.

Now: `A(s)` is computed over `Δ_P` only. The argument explicitly proves: (1) invisible declarations are ignored, so they cannot change `A(s)`; (2) the “conflict bit” is a deterministic function only of `P`‑visible data (`Δ_P` + visible sources), so mutual information wrt invisible state is zero.

The earlier leak path is eliminated by construction. The information‑theoretic argument is now formally correct relative to the new semantics.

**Conclusion (B): closed.**

---

**(C) T7 grounded in 0.44 precision & total extractor**

Previously: T7 was stated as a “theorem” justified by an empirical precision (0.44) and implicitly assumed total extraction.

Now: T7 is clearly a **design constraint**, with the experiment as the *motivation* only; no numerical constant appears in the rule. Admissible comparisons are limited to structural facts or pinned/typed `φ_f` that are partial (total-or‑`⊥`) and validated. Bottom is handled explicitly as non‑disagreement.

This removes the category error and the totality assumption.

**Conclusion (C): closed.**

---

**(D) Over‑reaching injection‑resistance claim**

Previously: “injection‑resistance” verged into robustness claims; composition of deterministic functions was incorrectly treated as a proof.

Now: T3″ cleanly defines injection‑resistance as (i) no payload as instruction, (ii) payload does not choose which classifier runs. It explicitly states a *proof obligation* (non‑interference lemma) still to be discharged, and distinguishes this from evasion (allowed).

The guarantee is narrowed to control‑flow integrity, not correctness. This is now an honest, technically defensible claim.

**Conclusion (D): closed, with a clearly marked open proof obligation (acceptable as such).**

---

**(E) Contradiction: observable soundness vs T7 suppression of dissent**

Previously: observable soundness required surfacing dissent; T7 blocked non-authority comparisons from entering `C`.

Now: T7.2 explicitly carves out comparisons between any observed source and the *resolved authority* (schema provides the pin). Dissent cards arising from pinned‑typed divergences are admissible into `C`. Additionally: “demote, not suppress” is elevated to an invariant, with a formal statement: no volume/selection gate may eliminate *all* representations of such a divergence; `C` gets a dissent card if the source is pinned‑typed, otherwise `H` must have an entry.

This resolves the prior logical incompatibility: T7 no longer blocks the very dissent §E requires. The new invariant is conceptually clear, though see Part 2(d) for operational tension.

**Conclusion (E): logical contradiction is fixed; some implementability subtleties remain.**

---

**(F) A4 narrowing vs earlier theorems (T3′/T5′)**

Previously: A4 was narrowed, risking that earlier proofs implicitly relied on stronger extraction robustness.

Now: the text explicitly audits T3′ and T5′ and argues they only used structural facts (edges, foreign keys), not value extraction. Given how those theorems are characterized, the dependence on A4 for value extraction is convincingly removed.

**Conclusion (F): closed, assuming prior T3′/T5′ statements really are value‑free as claimed.**

---

PART 2 – New contradictions / gaps

**(a) Consumer‑relative authority and determinism / leakage**

Authority is now **consumer‑relative** via `Δ_P`. Determinism within a fixed projection is preserved: for a given `P`, `A(s)` is a total function of `(Δ_P, E, φ)`.

Replayability: you now must fix not just the state, but also the consumer (or at least its read‑rights projection) in the replay model. That is not a bug, but it is a *new parameter* in the semantics. The protocol should say this explicitly: “determinism” and “replay” are parameterized by P (or by the visibility lattice).

Leakage between consumers: two consumers comparing their `A(s)` could infer that their projections differ (“you see `conflicted`, I see `missing`”), which is information *about access policy*, not source content. The information‑flow story is only about `P`‑invisible **content**, not about meta‑policy; the latter is out of scope. So this is not a contradiction, but the scope boundary should be stated.

**Verdict (a): logically consistent, but the relativity of `A(s)` and P‑parametrization of replay should be made explicit.**

---

**(b) T7.2 carve‑out and extraction for non‑authority sources**

The carve‑out: pinned‑typed comparison between *any* source and the **resolved authority** of `s`. The authority side uses a validated `φ_f` by definition. The non‑authority side: text says “a fresh, pinned‑typed value from a non‑α source that diverges… is admissible” – that presupposes the *same* pinned, validated `φ_f` is applicable on that source’s schema.

However, the text does not *explicitly* state: “for the non‑authority source, the same validated `φ_f` must be schema‑compatible and used; no open extractor is allowed here.” It’s implied but not formalized.

Without that explicit constraint, there is a small hole: a careless implementor could read this as “resolved authority supplies the schema; any extractor that yields a typed value against that schema is allowed on the other side,” re‑introducing unvalidated extraction.

**Verdict (b): needs minor tightening. Require that both sides of a dissent comparison use the *same* validated pinned `φ_f` over schemas that are statically declared as compatible. Add that to T7.2’s definition.**

---

**(c) Partial `φ_f`, `⊥ → Unknown[unobserved]`, and consistency**

Authority state uses `⊥` as “unobserved” (never contributes to conflict). Guarded semantics define `Unknown[unobserved]` when `φ_f=⊥`. Observable soundness clauses treat these as “withheld / downgraded.”

I do not see a semantic inconsistency:

- For authority: if a would‑be maximal α has `φ_f=⊥`, it is effectively ignored → leads to `Unknown[unobserved]` rather than `conflicted`.
- For comparisons: `⊥` vs `v` is explicitly “structural incomparability, not disagreement” → `Unknown[unobserved]`.

This is coherent. The one corner that might deserve a one‑line clarification: if *both* sides are `⊥`, the system does not assert agreement; it should also map to `Unknown[unobserved]`. That is strongly implied, but not stated.

**Verdict (c): semantically consistent; optionally clarify “⊥ vs ⊥” as `Unknown[unobserved]` to avoid ambiguity.**

---

**(d) “No volume gate may eliminate all representations” vs hard budget**

There is a tension: if there is a hard cap on `|C| + |H|`, but dissents are unbounded, insisting that *every* divergence has at least one card in `{C∪H}` risks overflow.

The current text partially addresses this: agreement cards *may* be suppressed by volume gates; dissents must not be *entirely* suppressed. Two interpretations:

- **Per‑divergence invariant** (as written): every distinct divergence must have a representation. Under a strict global cap, this can become impossible. You either violate the invariant or the cap.
- **Best‑effort under capacity**: when the total number of divergences exceeds capacity, you select a subset but can drop some; then the invariant is violated.

As written, this is a **real conflict** unless the model assumes either (i) capacity is effectively unbounded for dissent (not claimed), or (ii) the invariant is conditional (“subject to a capacity constraint; if violated, emit a separate ‘overflow / unsound’ diagnostic”).

You need an explicit resolution in the formal story. Two easy ways:

- Introduce a higher‑priority *safety gate*: either the system must refuse to answer once dissent‑card demand exceeds capacity, or it must signal “truncation” as an additional, soundness‑relevant output.
- Or weaken the invariant: “For any divergence that the system *admits into the representation set under current capacity*, no downstream volume gate may remove *all* of its representations.”

Right now, the strong invariant plus a hard cap is contradictory in worst‑case scenarios.

**Verdict (d): unresolved; requires modification of the invariant or explicit overflow semantics.**

---

Overall verdict

Most of the round‑1 issues are genuinely fixed; the addendum is substantially stronger and more coherent.

Remaining items:

- Clarify P‑parametrization of replay / determinism (§B(a) above) – nit.
- Tighten T7.2’s carve‑out to require the *same* validated pinned `φ_f` on both authority and non‑authority sources (§B(b)) – minor but important.
- Clarify `⊥ vs ⊥` → `Unknown[unobserved]` (§B(c)) – nit.
- Reconcile “no volume gate may eliminate all representations of a divergence” with a hard volume cap, either by conditioning the invariant on capacity or by defining truncation/overflow behavior (§B(d)) – substantive.

**Final assessment: minor‑revision.** The remaining issues are localizable and do not undermine the main fixes, but they should be addressed before treating v0.5 as stable.