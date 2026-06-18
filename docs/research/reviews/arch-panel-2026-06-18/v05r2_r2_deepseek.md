**PART 1 — Closure confirmation (six issues)**  

1. **A (banned extraction for authority)** – Fixed. Authority now exclusively uses a pinned, typed, partial extractor `φ_f` (§A); `⊥` never creates conflicts. The old open‑ended extraction path is closed.  
2. **B (leaked invisible‑declaration existence)** – Fixed. The consumer‑visible projection `Δ_P` (§A, A7) ensures `A(s)` depends only on sources the consumer can already read. The argument that divergence over visible sources adds zero additional information is sound; the earlier leak is patched.  
3. **C (category error: measured precision 0.44 as a theorem)** – Fixed. T7 is restated as a design constraint with a normative precision bar τ (target ≥0.9). The 0.44 experiment is now correctly cited as motivation, not as a constant in a theorem. Extractors are required to be validated, deterministic, schema‑bounded, and partial with `⊥`.  
4. **D (over‑reaching injection‑resistance claim)** – Fixed. T3″ sharpens the guarantee to *control‑flow injection resistance* (no payload‑directed classifier selection), and explicitly separates evasion (input selection) as permitted. Uncandidated free‑text judges are relegated to `H`, consistent with T7.  
5. **E (fatal T7 vs. surfacing dissent)** – Fixed. The carve‑out T7.2 admits a pinned‑typed comparison between *any* source and the resolved authority’s value, enabling dissent cards in `C`. The “demote, not suppress” property is now checkable; observable soundness is reconciled.  
6. **F (A4 narrowing vs. T3′/T5′)** – Fixed. The audit shows T3′ and T5′ rely only on structural features (edges, reference existence), not on extracted field *values*. Narrowing A4 to validated pinned fields therefore does not affect those theorems.  

*All six issues are substantively closed.*  

---

**PART 2 — New‑contradiction hunt**  

**(a) Consumer‑relative authority, determinism, and replayability**  
`A(s)` is computed over the consumer‑visible projection `Δ_P`. This makes authority consumer‑relative, but that does **not** break determinism/replayability: the broker’s output remains a deterministic function of the full state and the requesting consumer’s identity (which is already required for authorization). Replay can fix the projection as part of the replay context. Two consumers seeing different `A(s)` leaks nothing about invisible sources to the consumer who cannot see them; the projection ensures the certificate reveals no information beyond what the consumer already knows from their own readable sources. No contradiction.  

**(b) T7.2 carve‑out and extraction for arbitrary sources**  
The dissent comparison uses the *resolved authority’s* validated, pinned `φ_f` as the extractor. If the arbitrary source does not have field `f` or extraction returns `⊥`, the result is a structural incomparability, not a dissent. No open‑ended extraction is re‑introduced; the extractor remains the same validated, schema‑bounded one. The hole remains closed.  

**(c) `⊥` interaction with authority definitions**  
`⊥` is consistently treated as unobserved: it never contributes to a conflict or a resolved state, and both the soundness clauses and the `Unknown[unobserved]` valuation align. No inconsistency.  

**(d) “No volume gate may eliminate ALL representations of a divergence” vs. a hard volume‑budget cap**  
This is a genuine new tension. The addendum mandates that for every divergence from the resolved authority, at least one dissent card must survive any volume/selection gate. If the gate is implemented with a fixed, small cap (as suggested by earlier volume‑budget thinking) and the number of divergences exceeds that cap, it is **impossible** to keep a representation for each divergence. The invariant then becomes unsatisfiable. The text does not qualify the cap or relax the property. This is a bug introduced by the “demote, not suppress” requirement; it needs clarification (e.g., the gate must be sized to accommodate all active dissents, or the property holds only when the cap is not exceeded).  

---

**Verdict: Minor revision**  

The six round‑1 issues are convincingly closed. The only new problem is the unresolved interplay between the “must represent every dissent” invariant and a potential fixed volume cap (item (d)). The authors should add a clear statement on how volume‑budget constraints interact with this obligation, and whether the cap is assumed to be large enough or if the property is conditional. Additionally, the T3″ non‑interference proof remains a sketch; while noted as a limitation, a formal lemma is still outstanding and should be pursued, but this does not block acceptance.  

**Recommended fixes**:  
- Clarify that the volume‑selection gate must be sized to never suppress *all* representations of any divergence (or declare a conditional property).  
- Optionally, strengthen the T3″ non‑interference sketch toward a mechanized lemma in the next revision.