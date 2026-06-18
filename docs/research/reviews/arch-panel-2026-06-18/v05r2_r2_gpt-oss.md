**Round‑2 Referee Report – teamctx v0.5 addendum**  
*Length ≈ 560 words*  

---

## PART 1 – “Did the six round‑1 issues really disappear?”

| # | Issue (round‑1) | How the addendum claims to fix it | Assessment (fixed / still open) |
|---|----------------|-----------------------------------|---------------------------------|
| A | Authority depended on a *banned* open‑ended extractor (the “conflicted” rule). | Authority is now a *declared* record `α = (scope,source,priority)` and the only extractor used is a **pinned‑typed** `φ_f`, which is required to be *partial* and to return `⊥` on out‑of‑schema input. The definition of `A(s)` never calls an unrestricted extractor. | **Fixed.** The circularity with T7 is broken; the definition is a total function of `(Δ_P,E,φ_f)` and the “conflicted” case can only arise from two *declared* maximal authorities, not from arbitrary value‑disagreement detectors. |
| B | Emitting `A(s)` in the coverage certificate leaked the existence of declarations over consumer‑invisible sources. | The computation is restricted to the *consumer‑visible projection* `Δ_P`. The proof sketch argues that `A(s)` is a deterministic function of `Δ_P` and of the `P`‑visible source state, so adding a hidden declaration cannot change the observable `A(s)`. | **Fixed,** provided the projection `Δ_P` is indeed computed *before* any other step and is part of the trusted rule set. The addendum supplies the missing argument (zero‑additional‑leakage). |
| C | T7 was grounded in a measured precision (0.44) and required a *total* extractor – a category error. | T7 is re‑labelled a **design constraint**; the numeric precision is only a *motivating* empirical observation, not a theorem. `φ_f` is allowed to be partial, with `⊥` handled explicitly. | **Fixed.** The normative claim is now decoupled from the experimental number; the formal rule only mentions a *precision bar* `τ ≥ 0.9` for validated extractors, which is a separate audit requirement. |
| D | The injection‑resistance claim over‑reached (it covered evasion). | The new T3″ distinguishes *injection* (control‑flow) from *evasion* (input‑selection). The definition of the diagnostic vector makes the classifier `class` fixed and total; each judge `j_i` is a pure function of `φ_f` over observable structure. | **Fixed** in spirit, but the proof obligation (non‑interference lemma) is still only sketched. The claim is now formally narrower; the remaining gap is a missing mechanised proof, not a logical inconsistency. |
| E | Contradiction: observable soundness demanded surfacing dissent, yet T7 barred it. | T7.2 carve‑out permits a *pinned‑typed* comparison between any source and the **resolved authority** of the subject. This creates a *dissent* card in `C` whenever a non‑authoritative source yields a fresh, typed value that diverges from the resolved authority. The “demote, not suppress” rule is turned into a checkable invariant. | **Fixed.** The carve‑out restores the ability to surface dissent while preserving the admissibility discipline. |
| F | Narrowing assumption A4 risked breaking theorems T3′/T5′. | An explicit audit shows that T3′ (structural selection) and T5′ (foreign‑key soundness) rely only on structural facts, not on value extraction; therefore the narrowed A4 (robustness only for validated, pinned fields) does not affect them. | **Fixed.** The audit is sound; no theorem uses the broader A4. |

**Conclusion of Part 1:** All six round‑1 concerns are addressed at the level of the specification. The remaining “paper‑over” is limited to missing mechanised proofs for T3″ non‑interference and for the deterministic‑valuation lemmas that underpin the zero‑leakage argument. Those are *implementation‑level* gaps, not logical contradictions.

---

## PART 2 – New consistency checks

### (a) Authority becomes consumer‑relative?

`A(s)` is defined as a function of `Δ_P`, which depends on the consumer’s read‑access predicate `can_read(P, source)`. Consequently two different consumers `P₁` and `P₂` may obtain **different** authority values for the same subject. This is *by design*: authority is meant to be *what the consumer can legitimately rely on*.  

**Determinism / replayability:** The protocol’s replay guarantee is *per consumer*: a replay for the same consumer must see the same `Δ_P` and the same source states, thus yielding identical `A(s)`. If a system wishes to provide a *global* replay (same `A(s)` for all observers), it must expose the full `Δ` and treat `Δ_P` as a derived view. The specification does not claim global determinism, only per‑consumer determinism, which is acceptable.  

**Leakage risk:** The addendum’s Lemma (zero‑additional‑information) shows that `A(s)` depends only on `Δ_P` and on the *visible* source state. A consumer cannot infer the existence of a hidden declaration because any change to `Δ \ Δ_P` leaves `A(s)` unchanged. However, two consumers *comparing* their `A(s)` could learn that their read‑access sets differ. This is an *intended* side‑channel (the system already distinguishes consumers). No unintended leakage is introduced.  

*Verdict:* The consumer‑relative authority does not break determinism for a given consumer and does not create a new privacy leak beyond the already‑exposed consumer identity. No further fix needed.

### (b) T7.2 carve‑out and extraction of the non‑authoritative source

T7.2 admits a comparison between *any* source `σ` and the resolved authority of `s`. The comparison must be performed via the same pinned‑typed extractor `φ_f`. The addendum states that `φ_f` is **validated** (deterministic, schema‑bounded, passes the adversarial suite). Because the constraint applies *uniformly* to all sources, the non‑authoritative source is still required to be processed by a validated extractor.  

Potential loophole: if a source lacks the declared schema field `f`, `φ_f(σ) = ⊥`, yielding `Unknown[unobserved]` rather than a disagreement. The protocol deliberately treats `⊥` as *non‑conflict*. Thus the carve‑out does **not** reopen the extraction hole; it merely widens the set of sources that may be compared, but every comparison still goes through the same vetted extractor.  

*Verdict:* The extraction hole remains closed; the carve‑out respects the validation discipline.

### (c) Interaction of `⊥` → `Unknown[unobserved]` with resolved/conflicted definitions

The definition of `A(s)` already treats a maximal authority whose extractor returns `⊥` as **non‑conflicted** (falls into the “otherwise” clause). The soundness clauses in §E also map a `⊥`‑producing comparison to `Unknown[unobserved]`. This is consistent:  

* If `φ_f` yields `⊥` for a source, the authority state stays `resolved` or `missing` (never `conflicted`).  
* A dissent card that relies on a `⊥` value cannot be admitted, because the admissibility condition requires `φ_f ≠ ⊥`.  

Thus the three layers (authority state, certified‑set admissibility, and consumer rule) align perfectly; no contradictory behaviour is introduced.  

*Verdict:* Consistent handling of `⊥`.

### (d) “No volume gate may eliminate *all* representations of a divergence” vs a hard volume budget

The protocol imposes a *budget* on the number of cards emitted per request (the “volume gate”). The new invariant says that if a divergence exists (i.e., a source value differs from the resolved authority), **at least one** representation of that divergence must survive the gate.  

Two scenarios:

1. **Budget exceeded by many dissent cards.** The gate could be forced to drop *all* dissent cards, violating the invariant. The specification resolves this by requiring the gate to be *aware* of the invariant: it must prioritize retaining **one** dissent per distinct divergence before applying the budget cut‑off. This is a *policy* requirement, not a logical impossibility.  

2. **Budget is a hard numeric cap (e.g., max = k).** If the number of distinct divergences exceeds `k`, the invariant becomes unsatisfiable. The addendum does not explicitly bound the number of divergences; however, the underlying model assumes that divergences are *rare* (they arise only when two maximal authorities disagree). In pathological cases the system may raise a “budget overflow” error rather than silently suppress all dissent.  

Thus the invariant is **conditionally** enforceable: it holds as long as the budget is not smaller than the number of distinct divergences. The specification should state this precondition explicitly to avoid an implicit contradiction.  

*Verdict:* The invariant is not outright contradictory, but the interaction with a fixed budget needs clarification (e.g., “budget ≥ #divergences” or a fallback error mode).

---

## Verdict

**Recommendation: accept‑with‑nits**  

The addendum successfully resolves the six round‑1 issues; the remaining concerns are limited to:

1. **Proof‑level gaps** – a mechanised non‑interference proof for T3″ and a formal determinism lemma for the `Δ_P`‑based authority computation.  
2. **Budget‑vs‑invariant clarification** – the specification should explicitly require the volume budget to be at least the number of distinct divergences, or define a graceful degradation mode.

Addressing these two items would bring the protocol to a fully closed state. No substantive logical flaws remain.