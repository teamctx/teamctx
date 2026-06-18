§A (Authority as a declared record)

Strongest objection: the definition of `A(s)` is underspecified with respect to “fresh typed values,” and conflicts with the T7 sharpening of φ.

- `resolved`/`conflicted` are defined in terms of “fresh typed values” of `source(α)`; but extracting typed values from sources is exactly the operation now tightly constrained by T7 and the scoped A4. In §A you do not state whether `A(s)`:
  - is computed *only* using pinned, typed φ_f (as in T7.2), or  
  - may rely on any φ, including open-ended extraction.

If the latter, `A(s)` secretly depends on the same empirically-unreliable extraction the rest of the protocol has banished from `C`, which reintroduces the A4 problem in the authority machinery. If the former, the text must say so: “fresh typed values” must be defined as values obtained via pinned, typed, schema-bounded extractors only.

Additionally, the “temporary” state is described informally (“supersedes steady-state authority within its window”) but not integrated into the `resolved`/`conflicted` cases. There is an implicit priority order between temporary and steady declarations, but the exact rule (e.g., does temporary always win even if stale?) is not formalized.

Recommendation: explicitly scope the evaluation of `A(s)` to T7-eligible extractions, and give a precise priority lattice (temporary vs priority, staleness) to make `A(s)` a total, deterministic function of `Δ` and `E`.


§B (Guarded semantics extension — typed Unknown)

Strongest objection: the claim that reporting `A(s)` in κ does not affect T2′/T6 is only partially argued and misses a realistic leakage mode.

The text says “`A(s)` ranges only over declared, P-visible sources in Δ; it carries no information about P‑invisible sources.” That is only true if, for every subject `s` included in κ:

- The set `applies(s)` is restricted to declarations over P-visible sources, *and*  
- The classification `resolved/missing/conflicted/temporary` is itself computable solely from P-visible data.

However, §A defines `applies(s) = { α∈Δ : s ∈ scope(α) }` without a projection wrt the consumer’s visibility. If Δ can contain sources not visible to the consumer, then a change from `Unknown[no_authority]` (no α) to `Unknown[conflict]` when a hidden declaration is added will leak existence of that hidden authority. Even if `Δ` is P-visible in principle, the implementation must enforce that κ only exposes authority states for subjects `s` that are already within the exposure budget for T6.

You are implicitly assuming “Δ is fully visible under P,” but that’s not stated as an assumption. As written, B’s non-leakage argument is incomplete.

Recommendation: add either (i) an explicit assumption “Δ is P-visible and contains no P-invisible sources,” or (ii) a construction that projects `A(s)` to a P-visible authority state (e.g., treat all effects of P-invisible declarations as `Unknown[no_authority]`).


§C (Certified-set restriction T7)

Strongest objection: the admissibility rule is directionally right but formally incomplete, and the use of the 0.44 precision number as a baked-in threshold is somewhat category-muddled.

- Soundness: Partitioning claims into (1) extraction-free structural and (2) pinned, typed comparisons is *sound* relative to your stated threat model: it isolates C from empirically-bad open extraction. That is consistent with the φ-scoping in A4.  
- Incompleteness: You do not characterize whether *all* safe value comparisons are of the form T7.2, or whether there exist other structured cases (e.g. multi-field, conditional comparisons) that ought to be admissible but are currently banned. As a protocol, that’s acceptable but should be acknowledged as conservative, not complete.
- “Pinned, total, validated φ_f” is under-specified: what constitutes validation? Is it an empirical precision/recall threshold? A schema conformance proof? As written it risks being a hand‑wave. You do at least *constrain* φ_f to schema-bounded fields, which is good, but you must say who certifies totality and how regressions are prevented.

On grounding in measured 0.44 precision: the *direction* (“precision ≈ 0.44 ⇒ not admissible into C”) is product-reasonable, but the *number* should not be normative protocol text. The structural principle is: “Empirically-demonstrated high FP extraction is not admitted into C; current disagreement detectors have such bad precision that they are out.” The measured result should be cited as a motivating example, not a threshold.

Recommendation: (i) spell out that T7 is deliberately conservative, not complete; (ii) define “validated” for φ_f (e.g., an offline test harness and upgrade policy); (iii) rephrase the 0.44 into “current detectors fail our precision bar,” leaving the bar a separate, tunable engineering parameter.


§D (Diagnostic-vector classification T3″)

Strongest objection: the injection-resistance argument is correct in structure but over-claims in phrasing.

An adversary can certainly craft payloads that flip individual judges `j_i` (e.g., by manipulating filenames to create or avoid symbol overlap); this is not a violation of T3′/T3″ because those judges are defined *only* in terms of φ-mediated features. What T3′/T3″ promise is: payload is never parsed as instruction, and the mapping from artifact graph to `J(c)` and `class(J(c))` is deterministic.

Your text suggests T3″ “inherits … injection-resistance” as if that guarantees that adversaries cannot influence the class. Formally, what you can claim is:

- If every `j_i` is computable as a function of φ over observable structure, and `class` is total and fixed, then no *instructional string* in payload can cause the broker to execute arbitrary behavior.  
- But a malicious user can choose payload that changes φ’s output in adversary-controlled ways. That’s *allowed*; injection-resistance here is about control flow, not classifier robustness.

Recommendation: sharpen wording: explicitly define “injection-resistance” as “no direct use of unconstrained payload as instructions / prompts,” and acknowledge that adversaries can still steer J(c) via the structured features themselves.


§E (Authority and observable soundness)

Strongest objection: the “demoted, not suppressed” rule is conceptually consistent with v0.3 but is not yet a checkable protocol property.

- Consistency: v0.3 observable soundness allowed under-approximation but not fabrication or hiding of true, certifiable facts. Saying that non-authoritative dissent is surfaced (demoted, not suppressed) conforms precisely to that: a fresh, divergent, typed value is not erased.
- Underspecification: “demoted, not suppressed” needs a formal place in the observable. Is dissent:
  - always in H,  
  - sometimes in C but down-ranked, or  
  - in a separate “dissent” channel?

Without a precise rule, it is hard to prove the invariant “no fresh, pinned-typed divergence is fully hidden.” E’s bullets talk about cards and volume gates, but the protocol abstraction is ⟨C, κ⟩ and H; you must say exactly which layer dissent lives in, and whether volume gating may ever zero it out.

Recommendation: add a formal constraint: e.g., “For any subject/source pair where a fresh, pinned-typed value diverges from a resolved authority, either there exists a dissent element in C or in H (tagged as uncertified); no volume gate may eliminate all such representations.” That makes “demote, not suppress” a property, not a slogan.


§F / Overall consistency with v0.3/v0.4

No outright contradictions with v0.3/v0.4 are introduced; the main risk is *silent broadening*:

- A4 sharpening is good, but §A’s use of “fresh typed values” is not explicitly bound to this new scope, which could reintroduce the old A4 blanket assumption implicitly.
- The promise that κ reporting A(s) preserves T2′/T6 is only valid under an unstated visibility assumption on Δ.
- T3″ composition is consistent with T3′’s semantics, as long as “feature-mediated” for each j_i is enforced.

Verdict: **minor-revision**.

Required fixes:

1. §A: Make `A(s)` explicitly depend only on T7-eligible pinned, typed extraction; formalize temporary vs steady-state priority and freshness so `A(s)` is total and deterministic.
2. §B: Add either (a) an assumption that Δ is fully P-visible, or (b) a projection of A(s) that masks any influence of P-invisible declarations, and adjust the T2′/T6 argument accordingly.
3. §C: Clarify “validated φ_f” (what constitutes validation; how totality is maintained) and rephrase the precision=0.44 discussion as motivation, not a fixed threshold; explicitly note that T7 is conservative, not complete.
4. §D: Refine the injection-resistance claim to match the formal notion (no payload-as-instruction), not robustness to adversarial feature manipulation.
5. §E: Give a formal rule for where dissent appears (C vs H) and a constraint ensuring it cannot be fully suppressed by volume/selection, making “demote, not suppress” verifiable.