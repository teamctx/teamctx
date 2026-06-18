# teamctx Protocol — v0.5 addendum (applied on v0.3 + v0.4)

*New-content addendum (not a review round). It formalizes three decisions from the
[architecture record](../product/vision/architecture-decision.md) that extend the
model: **authority** as a first-class declared record (D6); the **certified-set
restriction** that follows from the [undeclared-disagreement experiment](reviews/arch-panel-2026-06-18/disagreement-experiment-result.md);
and **diagnostic-vector classification** (T3′ → T3″). All of v0.3/v0.4 carries over
unchanged. Notation continuous with prior versions: subjects `s∈S`, observations,
evidence state `E(s)`, certified card set `C`, coverage certificate `κ`, untrusted
hint layer `H`, meta-theoretic valuation `⟦·⟧`, sound consumer rule `⟦·⟧⁻`,
declassification dial `δ`, assumptions `A1–A5`.*

> **Revision note (round-1 referees, 2026-06-18).** Refereed by a 4-model panel
> (2 minor-revision, 2 major-revision; bugs convergent). This revision closes all six:
> (1) authority no longer depends on banned extraction — it is scoped to pinned-typed
> `φ_f` (§A); (2) the T2′ leak is patched by computing authority over the
> consumer-visible projection `Δ_P` with an explicit zero-additional-leakage argument
> (§B); (3) T7 is restated as a **design constraint** with a precision bar, not a
> theorem grounded in a measured number; `φ_f` is partial with `⊥`-handling (§C);
> (4) the T3″ guarantee is sharpened to *injection*-resistance and distinguished from
> *evasion* (§D); (5) the §E↔T7 contradiction is resolved by a T7.2 carve-out for
> comparison against the resolved authority, and "demote, not suppress" is made a
> checkable property (§E); (6) A4-narrowing is audited against T3′/T5′ (§F). Reports:
> [`reviews/arch-panel-2026-06-18/v05_ref_*.md`](reviews/arch-panel-2026-06-18/).
>
> **Round-2 (confirming) referees, 2026-06-18.** All six unanimously confirmed closed;
> verdict accept-with-nits / minor-revision, converging on a single fix — the
> volume-budget vs. dissent-preservation **pigeonhole** — resolved here via
> `Unknown[truncated]` (§B/§E), plus consumer-relative determinism (§A) and the
> same-`φ_f` / resolving-schema clarifications (§E). Reports:
> [`v05r2_*.md`](reviews/arch-panel-2026-06-18/). Remaining (acknowledged,
> non-blocking): the T3″ non-interference lemma and mechanized proofs.

---

## §A. Authority as a declared record

Authority answers *what should be true*. It is a **governance declaration, not an
inferred fact** — it enters the trusted rule set the way `deps_G` does, never read
from source content as instruction.

**Declaration.** `α = (scope, source, priority)`; declaration set `Δ` supplied
out-of-band (checked-in `.teamctx`, or the durable layer). **Consumer projection
(A7, new):** authority is computed over the consumer-visible projection
`Δ_P = { α∈Δ : can_read(P, source(α)) }`, never over `Δ` directly; declarations over
`P`-invisible sources contribute nothing to the consumer's authority state. Let
`applies_P(s) = { α∈Δ_P : s ∈ scope(α) }`.

**Extraction is pinned (closes the §A↔T7 circularity).** All authority values are
obtained via a **T7.2-eligible pinned, typed extractor** `φ_f` over a declared
schema field `f`; `φ_f` is **partial**, returning `V ∪ {⊥}` (`⊥` = out-of-schema /
extraction failure). Authority never uses open-ended extraction — the operation T7
restricts — so the 0.44-precision problem does not enter the authority machinery.

**Authority state** — a total, deterministic function of `(Δ_P, E, φ)`:
```
A(s) =
  conflicted  if ≥2 priority-maximal α∈applies_P(s) with E(source(α))=fresh and
                φ_f(source(α)) ≠ ⊥, whose values differ under field f's typed equality
  resolved    if exactly one priority-maximal α survives with E=fresh, φ_f ≠ ⊥
                (a fresh, in-window temporary override α_t is priority-maximal by
                 construction; if α_t is stale or φ_f(α_t)=⊥, it is dropped and
                 steady-state authority is reconsidered)
  missing     if applies_P(s) = ∅
  (otherwise) the subject contributes Unknown[unobserved] — e.g. the sole maximal
                α has E≠fresh or φ_f=⊥ — never conflicted
```
`⊥` never participates in divergence: an unextractable value yields
`Unknown[unobserved]`, not a conflict (closes the referees' `⊥`-handling gap).

**Determinism is per consumer.** Because `A(s)` is computed over `Δ_P`, it is
consumer-relative — write `A(s, P)`; `κ` is consumer-specific and replay fixes the
principal `P` (its `can_read`). Two consumers observing different `A(s)` is a standard
ACL-view property, not a protocol leak: each consumer's observable is a function of
its own `Δ_P` only, so T2′ holds per consumer.

**A6 (assumption, clarified).** Declarations in `Δ` are trusted, authentic governance
input. A6 is a **governance-authenticity** assumption only; it does **not** assume
extraction correctness — extraction is governed by T7.2, not A6.

---

## §B. Guarded semantics extension — the typed `Unknown`

Refine the meta-theoretic valuation to carry a reason (each demands a different
consumer action):
```
⟦ρ⟧ ∈ { True, False,
         Unknown[unobserved],   -- a dep σ∈deps_G(ρ) has E(σ)∈{missing,unreachable,partial}, or φ_f=⊥
         Unknown[no_authority],  -- A(subject(ρ)) = missing
         Unknown[conflict],      -- A(subject(ρ)) = conflicted
         Unknown[truncated] }    -- a real divergence omitted under volume budget (§E), not silently dropped
```

**The broker still emits no valuation** (v0.4 B1 preserved): it emits `⟨C, κ⟩`, and
`κ` reports the categorical `A(s)`.

**T2′/T6 preserved — now with the argument the referees demanded.** Two channels were
raised; both are closed by the `Δ_P` projection (§A):

1. *Invisible-declaration existence.* Because `A(s)` is computed over `Δ_P` (only
   declarations the consumer can read), adding or removing a `P`-invisible declaration
   cannot change the consumer's observed `A(s)`. So no flip (`resolved↔conflicted↔
   no_authority`) leaks the existence of a `P`-invisible source. (This requires A7;
   without the projection, the original claim was false — the panel was right.)
2. *Divergence bit over visible sources.* When `A(s)=conflicted`, the consumer learns
   that two `P`-**visible** sources diverge on field `f`. But both values are
   obtained by `φ_f` over sources the consumer can already read; the divergence bit is
   a **deterministic function of already-`P`-visible data**, hence **zero additional
   information** beyond the consumer's own view. Formally, the observable `A(s)` is a
   function of `Δ_P` and `P`-visible source state only, independent of `P`-invisible
   state ⇒ the single-shot mutual-information bound of v0.4 T6 is unchanged (its
   domain is `P`-visible data; `A(s)` adds no `P`-invisible-dependent term). ∎

The sound consumer rule `⟦·⟧⁻` gains obligations: `Unknown[conflict] ⇒ escalate (do
not pick)`; `Unknown[unobserved] ⇒ gather`; `Unknown[no_authority] ⇒ treat candidates
as unranked dissent`. All remain `≠ False`.

---

## §C. Certified-set admissibility — T7 as a *design constraint*

**T7 is a design constraint, not a theorem.** Protocols make normative claims;
experiments make descriptive ones. The [experiment](reviews/arch-panel-2026-06-18/disagreement-experiment-result.md)
(two deterministic detectors, precision 0.44 on a 48-item adversarial corpus, FPs in
representation + superseded-section, free-text recall 0) is the **motivating
evidence** that current open-extraction disagreement detectors fail the bar — it is
**not** a normative constant and does **not** prove a universal negative.

**T7 (admissibility constraint).** A claim is admitted to `C` only if it is:
1. **Extraction-free structural** — a fact over explicit graph edges and change-state
   (e.g. "`a₁` and `a₂` both changed since branch point and both link `s`"); or
2. **Pinned-typed comparison** — a comparison of field `f` where `φ_f` is a
   **validated, partial (total-or-`⊥`)** extractor over `f`'s declared schema, and the
   comparison is licensed either by a declared authority `α∈Δ_P` **or by the resolved
   authority of `s`** (the §E carve-out).

`φ_f` is **validated** iff: deterministic; schema-bounded (returns `⊥`, never a
guess, on out-of-schema input); and passes a fixed adversarial conformance suite at a
precision bar `τ` (target `≥0.9`) with a stated regression/upgrade policy. **`⊥`
comparisons** are structural incomparabilities, not disagreements: `⊥` vs `v` ⇒
`Unknown[unobserved]`, never `disagree`.

All other value-(dis)agreement claims — undeclared open-extraction comparisons — are
**not admissible to `C`**; they may appear only in `H`, uncertified. **T7 is
deliberately conservative, not complete:** other safely-decidable structured
comparisons may exist and are excluded by design until they clear `τ` on an
independently-audited adversarial corpus.

**Corollary (A4 scoped).** A4 (φ-robustness) is now bounded: `φ` is relied upon
**only** for validated, pinned, typed fields (T7.2). Open-ended extraction is not
assumed robust — empirically it is not — and the protocol keeps it out of `C`.

---

## §D. Diagnostic-vector classification (T3′ → T3″)

T3′ established *feature-mediated selection*: cards are selected by a typed extractor,
not by reading payload as instruction. T3″ generalizes to a **vector of deterministic
judges**.

**Definition.** For a candidate `c`, `J(c) = (j₁,…,j_k)`, each `jᵢ ∈ {1,0,⊥}`, each a
feature-mediated typed judgment (`j_file`, `j_symbol`, `j_semequiv`, …). A fixed total
classifier `class : {1,0,⊥}^k → Class` maps the *pattern* to a card class
(`(j_file=1, j_symbol=0) → phantom-overlap → suppress`, etc.).

**T3″ (injection-resistance, precisely stated).** "Injection-resistance" means
**(i)** no payload is interpreted as instruction/prompt, and **(ii)** no payload
determines *which* classifier runs. Both hold: each `jᵢ` is a feature-mediated
function of `φ` over observable structure, and `class` is fixed and total — so no
payload alters control flow or the classifier. *Proof obligation:* a non-interference
lemma that each `jᵢ` is a **pure function of `φ` over observable structure** with no
payload-directed control flow (stated as the formal target; current argument is a
sketch — the referees correctly flagged that composition alone is not a proof).

**Evasion is distinct and permitted.** An adversary *can* craft a payload to
deterministically set a feature (e.g. whitespace flips `j_semequiv`) and thereby steer
the class. This is **input selection, not injection** — it is expected and allowed.
Consequence: judges relying on open-ended/free-text features are **best-effort and
uncertified** (their cards stay in `H`, per T7); only pinned/typed judges yield
certified classes. T3″ guarantees control-flow integrity, *not* classifier robustness
to adversarial feature choice.

---

## §E. Authority and observable soundness (resolving §E ↔ T7)

The round-1 panel found a fatal contradiction: §E requires non-authoritative dissent
to be surfaced (for observable soundness), but T7 admitted only declared-authority
comparisons to `C`. **Resolution: T7.2 is carved to admit a pinned-typed comparison
between *any* observed source and the *resolved authority* of `s`** (the resolved
authority's field schema is the pin). A fresh, pinned-typed value from a non-`α`
source that diverges from the resolved authority is therefore an **admissible `C`
member** — a *dissent* card.

Restating observable soundness relative to `Δ_P`:
- A `resolved` authoritative-value card is **sound** iff `E(source(α))=fresh` and
  `φ_f(source(α)) = v ≠ ⊥` under a validated pinned `φ_f`; else withheld / downgraded
  to `Unknown[unobserved]`.
- A `conflicted` card is **sound** iff ≥2 priority-maximal declarations have fresh,
  pinned-typed, divergent (≠⊥) values; it asserts *that* they diverge, never *which*
  is correct.
- **Demote, not suppress — now a checkable property.** For any `(source, field)` with
  a fresh, pinned-typed value diverging from the resolved authority: if the source is
  pinned-typed, a **dissent card exists in `C`** (tagged `dissent`); otherwise a
  representation exists in `H`. The dissent comparison reuses the **same validated
  `φ_f`** applied to the non-authority source (no new extractor; non-conformant input
  → `⊥` → `Unknown[unobserved]`, so the carve-out opens no extraction hole); the pin
  is the schema of the **resolving declaration**, not the derived state `A(s)`.
  **No divergence is *silently* suppressed:** it is represented in `C`/`H`, or — when
  the volume budget cannot hold a representation of every distinct divergence —
  surfaced as `Unknown[truncated]` in `κ`. This resolves the budget-vs-invariant
  pigeonhole the panel found: the hard cap is respected, omissions are explicit, never
  silent. Agreement with the resolved authority carries no information and *may* be
  suppressed. `⟦·⟧⁻` gains a demotion case: a dissent surfaces as
  `Unknown`-relative-to-authority, never `False`.

---

## §F. Updated assumptions, A4 audit, limitations

**Assumptions.** A1–A3, A5 (v0.3) carry over. **A4 sharpened** (T7 corollary: `φ`
relied on only for validated pinned typed fields). **A6 clarified**
(governance-authenticity, not extraction-correctness). **A7 (new):** authority is
computed over the consumer-visible projection `Δ_P`.

**A4 audit (closes the round-1 internal-inconsistency flag).** Narrowing A4 does not
break the prior theorems, because neither relied on value-extraction correctness:
- **T3′** selects on *structural features* (presence of edges/overlap), not on
  extracted field *values* — it survives the narrowed A4 unchanged.
- **T5′** (foreign-key observable soundness) concerns *reference existence* (a
  structural fact about links), not value extraction — survives unchanged.
A4-narrowing constrains only value-(dis)agreement claims, which v0.5 confines to
T7.2/pinned. No prior proof used A4 for value extraction.

**Limitations (honest scope).**
- **Undeclared open-extraction value-disagreement is out of `C`** (T7) — by
  measurement and design, not preference; it lives in `H`. Revisit only by beating
  `τ` (≥0.9) on an independently-audited adversarial corpus.
- **Authority resolves declarations, not governance** — `conflicted` is surfaced,
  never adjudicated.
- **T3″ phantom suppression is best-effort on free text**; certified only where its
  judges are pinned/typed. Control-flow integrity is guaranteed; classifier robustness
  to adversarial feature choice is not.
- **Proof obligations outstanding:** the T3″ non-interference lemma, and a mechanized
  artifact for the determinism / noninterference / guarded-semantics lemmas (v0.4).

---

*Status: round-1 + round-2 referee fixes applied; design spec **closed for round 2**
(accept-with-nits, all six round-1 issues confirmed closed, the one new pigeonhole
resolved). Remaining proof obligations (non-blocking): T3″ non-interference lemma;
mechanized proofs. Open product item: severity calibration (needs deployment
telemetry).*
