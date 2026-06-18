**PART 1: Confirming Closure of Round-1 Issues**

The v0.5 revision successfully addresses the six major flaws from Round 1. 

*   **(A) Authority circularity:** *Closed.* Scoping authority extraction strictly to a pinned, typed, partial extractor ($\phi_f$) severs the dependency on the banned open-ended extraction.
*   **(B) Invisible-source leakage:** *Closed.* Parameterizing authority over the consumer-visible projection ($\Delta_P$) restricts the domain of $A(s)$ to already-visible data. The zero-additional-leakage argument is now formally sound.
*   **(C) T7 category error:** *Closed.* Reclassifying T7 as a normative design constraint with a precision threshold ($\tau \ge 0.9$), rather than a theorem based on a single 0.44 measurement, restores meta-theoretic sanity.
*   **(D) Injection-resistance over-reach:** *Closed.* The distinction between control-flow integrity (injection) and adversarial feature manipulation (evasion) is precise, standard, and correctly bounds the T3″ guarantee.
*   **(E) Observable soundness vs. T7:** *Closed.* The T7.2 carve-out elegantly resolves the contradiction. By using the *resolved authority’s* schema as the pin, the protocol safely admits certified dissent without reopening the open-extraction floodgates.
*   **(F) A4 narrowing impact:** *Closed.* The audit correctly verifies that T3′ and T5′ rely on structural graph properties and reference existence, not value extraction. Narrowing A4 preserves prior proofs.

**PART 2: New-Contradiction Hunt**

The fixes introduce a much tighter protocol, but edge cases remain in the newly defined boundaries:

**(a) Consumer-relative Authority ($\Delta_P$) and Determinism:**
Because $A(s)$ is computed over $\Delta_P$, authority is now formally a function of the principal: $A(s, P)$. Determinism and replayability are preserved *provided the cache/replay key includes the principal's visibility context*. Cross-principal leakage (Consumer 1 seeing `resolved` while Consumer 2 sees `missing`) is a standard property of ACL-filtered views, not a protocol-level cryptographic leak. The protocol is safe here, but implementations must explicitly key state by $P$.

**(b) Extraction hole in the T7.2 carve-out:**
The carve-out permits comparing *any* observed source against the resolved authority. Does this reopen the extraction hole? No, because the text specifies the comparison must be "under a validated pinned $\phi_f$". If an adversary supplies an arbitrary, unstructured source, the schema-bounded $\phi_f$ will deterministically fail and return $\bot$. The text correctly notes that $\bot$ yields `Unknown[unobserved]`, not a dissent. The hole remains closed.

**(c) Partial $\phi_f$ and $\bot$ interactions:**
The handling of $\bot$ is logically consistent. In the authority calculation, $\phi_f = \bot$ causes the declaration to be safely dropped (preventing an adversary from causing a `conflicted` state by injecting malformed data into a high-priority source). In the soundness clauses, $\bot$ correctly degrades to `Unknown[unobserved]`. 

**(d) Volume gate vs. Dissent invariant (BUG FOUND):**
The text introduces a hard invariant: *"No volume gate may eliminate ALL representations of a divergence."* This creates a fatal pigeonhole contradiction with a strictly bounded volume budget. 
If the volume budget is $B$ cards, and an adversary generates valid, pinned-typed dissents across $B+1$ *distinct* fields or subjects, the broker cannot satisfy both constraints. It must either blow the budget (violating resource bounds) or drop all representations of at least one divergence (violating the new invariant). 

**Verdict: MINOR REVISION**

The v0.5 addendum is a massive improvement and structurally sound, successfully closing the Round 1 gaps. However, the contradiction in 2(d) must be patched before acceptance. 

**Required Fix:**
Resolve the pigeonhole contradiction between the volume gate and the dissent invariant. Introduce a formal `truncated` state or fallback mechanism. For example: *If the volume budget is exhausted by distinct required dissents, the broker must emit an `Unknown[truncated]` valuation for the omitted fields/subjects rather than silently suppressing them or exceeding the budget.* 

Once this truncation semantics is added, the protocol addendum is ready for baseline acceptance and mechanization.