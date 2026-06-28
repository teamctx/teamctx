# Referee Report: teamctx Protocol v0.5 Addendum

## Overall Assessment

This addendum formalizes three architectural decisions that extend the v0.3/v0.4 model. The work is substantive and the decisions are well-motivated by the cited experiment. However, several sections introduce formal gaps that must be closed before the addendum can be accepted as a coherent extension of the prior protocol. My verdict is **minor-revision**, with the specific fixes below.

---

## Section-by-Section Analysis

### §A: Authority as a Declared Record

**Strongest objection:** The definition of `A(s)` is underspecified at a critical boundary. The four-way classification depends on "fresh typed values" from sources, but the protocol never defines what constitutes a *typed value* in the authority context. Is it the raw payload? The output of `φ`? If `φ` is involved, then authority resolution inherits the T7 restriction (pinned-typed only), which the text does not acknowledge. Furthermore, "diverge" for `conflicted` requires a comparison operator that is never specified, is it structural equality, byte-equality, or `φ`-mediated semantic equivalence? Without this, `conflicted` is not deterministically computable.

**Verdict:** The state machine is well-structured, but the comparison primitive must be explicitly defined. Add: "Values are compared via the pinned-typed extractor `φ_f` for field `f`; divergence is `φ_f(source₁) ≠ φ_f(source₂)` under the equality of the field's declared type." This also makes explicit that A6's trust assumption does not extend to value extraction, it is a governance-input trust, not an extraction-correctness trust.

---

### §B: Typed Unknown

**Strongest objection:** The claim that "this does not reopen T2′" requires a tighter argument than the one provided. The text asserts that `A(s)` ranges "only over declared, P-visible sources in Δ" and therefore carries no information about P-invisible sources. But `Unknown[conflict]` is emitted when ≥2 priority-maximal declarations have *divergent fresh typed values*. If those sources are P-visible, their values are P-visible, and the *fact of their divergence* is a function of those values. The consumer learns that two P-visible sources disagree, this is a 1-bit leakage about the *relationship* between those sources' values. Is that within the single-shot bound? The v0.4 T6 bound was over the existence of a single P-invisible source; here the leakage is over the *joint distribution* of two P-visible sources. This is a different channel.

**Required fix:** Either (a) prove that the divergence bit is a deterministic function of the already-leaked visible values (which would make it zero additional leakage), or (b) acknowledge a new, bounded leakage term and bound it. The latter is more honest: the consumer learns "sources α₁ and α₂ disagree on field f," which is a 1-bit function of the visible declarations' values. Since the values themselves are already visible (they're in Δ-declared sources), this is *zero additional information* beyond what the consumer already has from the visible sources. Make this argument explicit.

---

### §C/T7: Certified-Set Admissibility

**Strongest objection:** This is the most important and most vulnerable section. The admissibility partition is well-motivated by the 0.44 precision result, but grounding a *formal protocol rule* in a single empirical measurement is a category tension. Protocols make normative claims; experiments make descriptive ones. The 0.44 result tells us that *two specific detectors* on *one specific corpus* performed poorly. It does not prove that *no possible extractor* can achieve high precision on undeclared comparisons. T7 asserts a universal negative ("all other value-equality claims are not admissible") based on a single positive failure.

**The fix:** T7 should be stated as a *design constraint*, not a theorem. "T7 (Design constraint): The protocol *does not admit* undeclared value-equality claims to C because the measured precision of state-of-the-art detectors on an adversarial corpus is 0.44, and the protocol's soundness requirement demands precision ≥ 0.9. Any future proposal to admit such claims must demonstrate precision ≥ 0.9 on an independently-audited adversarial corpus." This preserves the empirical grounding without making the protocol claim a universal negative that the experiment cannot support.

**Second objection:** "Pinned, total, validated `φ_f`" is hand-waved. What does "validated" mean? By whom? Against what? This is a critical dependency for the entire T7.2 pathway. The protocol must specify the validation criteria: `φ_f` is validated iff it passes a conformance suite of at least N adversarial examples and its output is deterministic and total over the field's declared schema. Without this, T7.2 is a hope, not a restriction.

---

### §D/T3″: Diagnostic-Vector Classification

**Strongest objection:** The inheritance argument ("composition of feature-mediated judgments under a fixed classifier is feature-mediated") is correct in structure but the text does not address the *adversarial* case. An adversary who controls the payload can craft it to influence a judge's output. Since each judge `jᵢ` is feature-mediated (it reads structure, not instruction), the adversary cannot *inject* a judge outcome. But can the adversary *cause* a specific judge outcome by manipulating the payload's features? Yes, that's the whole point of the features. The adversary can craft a payload that causes `j_file=1` and `j_symbol=0` (phantom overlap) or `j_file=1` and `j_symbol=1` (real collision). This is not injection-resistance; it's *feature manipulation*. The protocol must distinguish these.

**Required fix:** T3″ inherits *determinism and replayability* from T3′, but the injection-resistance corollary is: "no payload can cause the broker to execute a different classifier." This holds. The adversary can influence *which class* is selected by manipulating features, but cannot influence *which classifier* is applied. Acknowledge this distinction: "Feature manipulation is possible and expected; injection (changing the classifier logic) is prevented."

---

### §E: Authority and Observable Soundness

**Strongest objection:** "Demote, not suppress" is stated as a principle but not formalized. What does "demote" mean operationally? Does the card move from `C` to `H`? Is it emitted with a different `κ`? The v0.3 protocol defines `C` as the certified set and `H` as the untrusted hint layer. If a non-authoritative dissent card is "demoted," where does it go? If it stays in `C` but with a different classification, the protocol must define that classification. If it moves to `H`, then it's not "demoted", it's removed from `C`, which is suppression by another name.

**Required fix:** Define the operational semantics: "A non-authoritative dissent card is emitted in `C` with `κ` carrying `Unknown[conflict]` if the dissent is from a pinned-typed source; it is emitted in `H` if the dissent is from an unpinned source. In neither case is the card suppressed (withheld from emission)." This makes "demote" precise and verifiable.

---

## Internal Consistency with v0.3/v0.4

**New contradiction:** v0.4 T6 bounds single-shot leakage over *one* P-invisible source. §B introduces `Unknown[conflict]` which reveals that *two* P-visible sources diverge. If those sources are P-visible, this is zero additional leakage (as argued above). If either source is P-invisible, the conflict reveals its existence, which *does* violate T6. The text must explicitly restrict: "Authority declarations in Δ are P-visible by definition; no P-invisible source may appear in Δ." This is consistent with A6 (Δ is trusted governance input, reviewed) but must be stated.

---

## Verdict: Minor-Revision

**Required fixes:**
1. §A: Define the value-comparison primitive for `conflicted` detection; specify that it uses `φ_f` and is subject to T7.2.
2. §B: Add the explicit zero-additional-leakage argument for `Unknown[conflict]` (visible sources only).
3. §C/T7: Restate as a design constraint with a precision threshold, not a universal negative; define `φ_f` validation criteria.
4. §D: Distinguish feature manipulation (adversary controls class via features) from injection (adversary controls classifier logic).
5. §E: Define "demote" operationally (where the card goes in the C/H partition).

The addendum is substantively correct and the architectural decisions are sound. The gaps are in formal precision, not in design. With these five fixes, the addendum integrates cleanly with v0.3/v0.4.