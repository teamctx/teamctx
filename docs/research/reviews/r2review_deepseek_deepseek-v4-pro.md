# Referee Report: Resubmission v0.2

## 1. Resolution of Prior Defects

**(a) T5 reachability paradox (circularity in Req(q)):** RESOLVED. The shift to dangling references read from foreign keys *within* the observed subgraph cleanly breaks the circularity. Computing `D(q)` without traversing offline sources is the correct fix. The honest residual, structurally disconnected relevant sources, is properly admitted.

**(b) "Dissolve → relocate" overclaim:** RESOLVED. Dropping "dissolve" and making `κ` an explicit, machine-checkable ignorance boundary with the 3-valued semantics is a genuine improvement. The admission that correct consumption is an obligation the protocol cannot enforce (cited as agent-cooperation limitation) closes this.

**(c) T2 κ-leak / not-real-noninterference:** RESOLVED in the statement, PARTIALLY in the surrounding claims. The concession to "value-channel only" and the explicit exclusion of timing/cardinality side channels is honest. However, §5's proof sketch for T2′ still claims output *depends only on S|_P* under `δ=none`. If the graph walk over `Ĝ_P` is not constant-time and constant-memory-access, timing and cache state will depend on the full graph structure, including invisible nodes that affect traversal order of visible edges. This is a side-channel caveat they acknowledge in §8 but should not claim "depends only" without the qualifier in the theorem statement itself.

**(d) T3 payload-irrelevance unproven + agent-cooperation caveat:** RESOLVED. The introduction of typed feature extractor `φ` with a finite schema and no free-text predicate makes the claim provable. The "up to `quote` payloads" qualifier and the explicit scope that this protects *selection* but not *delivery* nor *agent consumption* is properly bounded. The corollary "injection-resistant selection" is now precise rather than hand-wavy.

**(e) T1 event-ordering + T4 misnaming:** RESOLVED. Explicit total-order assumption and snapshot-digest pinning (including rules