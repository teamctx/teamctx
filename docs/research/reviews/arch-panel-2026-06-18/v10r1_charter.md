You are refereeing a REVISION of a formal-protocol paper (teamctx, a deterministic,
no-LLM, read-only context broker for AI coding agents). The prior version (accepted)
established: observable soundness; a three-valued guarded semantics where the broker
emits only ⟨C, κ⟩ (certified card set + coverage certificate) and NEVER a valuation;
existence-privacy T5 across permission boundaries with a declassification dial δ over
*invisible-target dangling references* and a single-shot mutual-information bound T6;
feature-mediated injection-resistant selection; authority as a declared record
(resolved/missing/conflicted/temporary) computed over the consumer-visible projection Δ_P.

A senior reviewer raised five fixes; the revised sections are below. The headline fix
(#1): observable soundness previously depended on the consumer "verifying deps_G(ρ) is
complete," with the rigor hiding in the word **conservative**: so deps_G/completeness
was promoted to an EXPLICIT certificate object (`complete?`) plus a named obligation O1.

=== REVISED §5 (guarded semantics & observable soundness) ===
deps_G(ρ) ⊆ Σ = sources whose state can affect ρ, from (i) typed refs reachable from ρ's
subject, (ii) policy-mandated sources, (iii) query structure. deps_G is trusted-rule-set;
its correctness is the named obligation:
  O1 (deps_G soundness): deps_G(ρ) over-approximates the true dependency set of ρ.
  Discharged PER CONNECTOR by its declared reference schema; a connector able to emit a
  reference class deps_G does not model MUST declare it, else complete? returns
  incomplete[unmodeled-ref].
Completeness checker, a TOTAL function complete?:(Prop,κ)→{complete}∪{incomplete[r]}:
  complete                  every σ∈deps_G(ρ) in κ with E(source σ)=fresh, and deps_G(ρ) closed
  incomplete[dangling]      a typed ref reachable from ρ has an unobserved target (E∈{missing,unreachable,partial})
  incomplete[stale-dep]     some σ∈deps_G(ρ) present but E≠fresh
  incomplete[policy-gap]    a policy-mandated source for ρ's scope absent/non-fresh
  incomplete[unbounded]     deps_G(ρ) not finitely enumerable from the graph (implicit/free-text refs)
  incomplete[unmodeled-ref] a connector declared a class deps_G does not model (O1)
κ carries the per-subject dependency-closure status complete? consumes; the consumer runs
complete? itself. Valuation (oracle): ⟦ρ⟧=True if a card witnesses ρ; ⟦ρ⟧=False iff
complete?(ρ,κ)=complete and no witness; else Unknown[reason]. Broker emits no valuation.
Sound consumer rule ⟦·⟧⁻: True iff a card witnesses ρ; False IFF complete?(ρ,κ)=complete
& no witness; else Unknown[reason] carrying complete?'s tag.
THEOREM 2 (under O1): ⟦ρ⟧⁻=True⇒⟦ρ⟧=True and ⟦ρ⟧⁻=False⇒⟦ρ⟧=False. Sketch: True identical;
for False, complete?=complete requires every dep observed-fresh & closure gap-free, and by
O1 the consumer's deps_G misses no true dependency so the oracle also returns complete.
THEOREM 4 sketch now: an unobserved reference target makes complete? return
incomplete[dangling], forcing Unknown[unobserved].

=== REVISED §4 (κ and T1) ===
κ = per-source evidence states; per-§8 authority states; a per-subject dependency-closure
status; and a content-addressed snapshot reference (signed digest + retrievable snapshot
id). T1 (verifiable replay): the digest BINDS inputs; given the retrievable snapshot a
verifier can re-derive ⟨C,κ⟩ and confirm the binding, the digest alone verifies, it does
not reconstitute an unavailable snapshot. H (hint layer) is OUTSIDE the privacy contract;
if surfaced to a human it is first projected to Δ_P.

=== REVISED §8 (authority states) ===
M(s) = priority-maximal declarations in applies_P(s) (fresh in-window temporary outranks
steady-state; stale/⊥ temporary is not maximal). Freshness source-indexed E(source(α)):
  conflicted  if ≥2 α∈M(s) fresh, φ_f≠⊥, values differ under f's typed equality
  resolved    if the unique α∈M(s) is fresh and φ_f≠⊥
  missing     if applies_P(s)=∅
  Unknown[unobserved]  otherwise, esp. when the priority-maximal authority is stale or
              φ_f=⊥; a stale higher-priority authority is NEVER silently overridden by a
              fresh lower-priority one; its staleness surfaces.
Example: policy page declared authoritative over the ticket; policy page stale + ticket
fresh ⇒ A=Unknown[unobserved] ("authoritative source stale"), NOT resolved-to-ticket.

=== APPENDIX A (worked trace, abridged) ===
Inputs: O1 rounding.Apply github PR!4471 fresh (rewrites symbol); O2 ticket jira fresh v=5;
O3 "Rounding Policy" confluence stale⟨2d⟩ v=3 DECLARED authoritative; O4 shared-proto gitlab
unreachable (a dep of the symbol). Δ_P:{rounding→(confluence policy, HIGH)}.
ρ1="no open PR conflicts with rounding.Apply": O1 witnesses a conflict ⇒ collision card;
gitlab unreachable ⇒ complete?(ρ1)=incomplete[dangling]; consumer: collision card emitted
(certified), "no FURTHER conflicts" = Unknown[unobserved], not False.
ρ2="authoritative cap is v": M={policy(HIGH)}, confluence stale ⇒ A=Unknown[unobserved].
κ: sources{github:fresh,jira:fresh,confluence:stale,gitlab:unreachable};
authority{rounding-cap:unknown}; closure{ρ1:incomplete[dangling], ρ2:incomplete[stale-dep]};
delta:none.

=== YOUR REVIEW ===
PART 1, Did the five fixes close cleanly? Especially #1: is the soundness rigor now
genuinely carried by O1 + the total `complete?` checker, or did it just relocate the
hand-wave from "conservative" into "discharged per connector by its declared schema"?
PART 2, Hunt for bugs the fix may have INTRODUCED:
  (a) Is `complete?` actually TOTAL/decidable? The incomplete[unbounded] case ("deps_G not
      finitely enumerable"), is deciding that itself decidable, or circular?
  (b) **κ now exposes per-subject closure status. Does `incomplete[dangling]` leak the
      existence of an INVISIBLE-target dangling reference, reopening T5/T6 / bypassing the
      δ dial?** (The dial was precisely for invisible-target dangling refs.) Check hard.
  (c) Appendix A: does emitting a collision card (a witness ⇒ True for "a conflict exists")
      while reporting "no further conflicts = Unknown" type-check against the valuation, or
      is the proposition ρ1 conflated? Is the trace internally consistent with §5?
  (d) §8: is `Unknown[unobserved]` the right reason for a *stale authority*, or does it need
      a distinct tag (e.g. Unknown[stale-authority]) for the consumer to act correctly?
Verdict: accept / accept-with-nits / minor-revision / major-revision, with specific fixes.
~450-700 words. Do not rubber-stamp.
