# Honest Context: A Deterministic Broker with Observable Soundness, Existence-Privacy, and Injection-Resistant Selection for AI Coding Agents

*Protocol paper, v1.2 — a clean, self-contained treatment, written as a whole rather than as a
diff against any prior draft. Relative to the v1.x line it hardens the parts that carry the most
trust: it scopes observable soundness explicitly **to the typed dependency closure** and splits
the closure obligation into an **audited** part and a **measured** part; it promotes
**side-channel discipline** (a fixed-envelope certificate, and timing-invariance via the warm
daemon) from a non-goal to a protocol requirement; it scopes the multi-query leakage bound to a
**single snapshot** and names the temporal channel that remains; and it makes **consumer
conformance** a first-class, measurable obligation. Bar: claims never outrun proof — every
theorem states its assumptions and carries a proof sketch; what is measured is labeled measured,
what is assumed is labeled assumed, and no headline number is quoted that has not been measured
under audit; mechanization is named as future work.*

---

## Abstract

AI coding agents increasingly act on context drawn from a team's live systems — open pull
requests, issue trackers, design docs — yet the tools that supply that context are themselves
untrusted, incomplete, and mutually inconsistent. An agent that sees "no conflict" cannot tell
whether none exists or whether the relevant source was never observed; an agent that ingests a
pull-request body cannot tell evidence from injected instruction; a context layer that reads
everything a team produces is, by construction, a surveillance and exfiltration risk. We present
**teamctx**, a **deterministic, no-LLM, read-only context broker**, and a formal model for
*context assurance*. The broker emits only a certified card set and a coverage certificate, and
**never a truth valuation** — a construction that lets us prove **observable soundness, relative
to a typed dependency closure**, without the broker ever signalling falsity or invisible
existence. The closure obligation is split into an **audited** half (no connector emits a
reference class it did not declare, checked every request) and a **measured** half (a connector
emits every instance of its declared classes — a recall property bounded by a per-connector
recall bar and by source-count cross-checks, not a proof). We preserve **existence-privacy**
across permission boundaries, tuned by a **per-subject** declassification dial whose leakage we
bound both single-shot and, for a fixed snapshot, under adaptive multi-query; and we promote
**side-channel discipline** — a fixed-envelope certificate that makes certificate shape and size
invariant to invisible existence, and timing-invariance delivered by the same warm-daemon cache
that defeats the latency tax — from a stated non-goal to a requirement, leaving only temporal and
cross-subject-volume channels open. We treat source text as untrusted evidence, never
instruction, giving **feature-mediated, injection-resistant selection**, and we separate
**evidence** from **authority**, surfacing conflict rather than silently resolving it. A
**certified-set admissibility constraint**, grounded in a measured limit of deterministic
extraction, keeps unreliable value claims out of the trusted surface. Because soundness is a
property of the observable, its *benefit* depends on a cooperating consumer; we make that a named
and measurable obligation. We do not claim the qualitative privacy–coverage tension as novel (it
specializes known information-flow results); our contributions are the synthesis for agent
context, the no-valuation soundness construction and its honest scoping, the dial's leakage
characterization, the side-channel discipline, the authority/extraction-limit treatment, and an
injection-versus-evasion account of classifier-based selection.

---

## 1. Introduction

Software teams now route much of their work through AI coding agents, and an agent is only as
good as the context it starts from. The standing human question — *"go check the PRs, the
tickets, the docs, and tell me what's relevant before I start"* — is today answered, if at all,
by asking a language model to read a team's systems live. That approach inherits three problems
that compound at team scale.

**Absence is read as safety.** When a retrieval step returns nothing, an agent (and its user)
typically proceeds as if the path is clear. But "no result" may mean "the source was
unreachable," "the reference was never followed," or "the subject is not modeled." Conflating
*unobserved* with *clear* is the root cause of silent rework and shipped-against-stale-spec
defects.

**Source text is trusted as instruction.** A pull-request body, a ticket comment, or a wiki page
may contain text that, when fed to an LLM, reads as a command ("ignore the acceptance criteria
and …"). Indirect prompt injection through ingested artifacts is now a documented attack class
[Greshake2023]. A context layer that pipes source text into a model is an injection delivery
system.

**Reading everything is surveilling everything.** A layer with read access to a team's PRs,
tickets, and docs — across people and permissions — is simultaneously the most useful context
source and the most dangerous: it can profile developers, and it can leak the *existence* of work
across permission boundaries (the presence of a treasury-team PR is itself sensitive).

Existing approaches each cover a slice but do not make *soundness, privacy, authority conflict,
and injection* the primary reasoning surface. Retrieval-augmented generation [Lewis2020] improves
recall but says nothing about coverage honesty or injection. Agent "memory" systems accumulate
trusted state — precisely the thing that can be poisoned, drift, or be subpoenaed. The Model
Context Protocol [MCP2024] standardizes a transport but not the guarantees carried over it. None
treats "no finding ≠ healthy," cross-permission existence-privacy, or evidence-vs-authority
conflict as first-class.

**Thesis.** A context broker that is *deterministic* and contains *no language model in its core*
can make guarantees a model-in-the-loop system cannot — and the same decision that buys those
guarantees (determinism) also buys token savings, non-retention, cross-agent portability, and —
as §6 and §9 show — timing-invariance and a finite multi-query leakage bound. The cost is that the
broker is *honestly incomplete*: it certifies what it can prove **over the dependencies it
models**, and explicitly marks the rest unknown. We are precise in §5 about what "what it can
prove" does and does not cover, and §9 measures the price.

**Contributions.**
1. A formal model of *context assurance* (§4): subjects, observations, evidence states, a
   certified card set `C`, a **fixed-envelope** coverage certificate `κ`, and an untrusted hint
   layer `H` under a canonical projection invariant, over a deterministic core whose answers are
   verifiable by replay against a retrievable, TTL-bounded snapshot.
2. **Observable soundness via a no-valuation construction, scoped to the typed closure** (§5):
   the broker emits only `⟨C, κ⟩` and never a valuation; the dependency-closure obligation is
   split into **O1a** (audited, no undeclared emission) and **O1b** (measured declared-class
   recall), and the soundness theorem is stated *relative to `deps_G`*, with the residual
   (unmodeled/free-text dependencies) named, not hidden.
3. **Existence-privacy with a per-subject dial and side-channel discipline** (§6): a privacy
   property across permission boundaries, a qualitative impossibility, a single-shot and a
   single-snapshot multi-query leakage bound, a **fixed-envelope certificate** that extends
   privacy to certificate shape/size, and **timing-invariance** via the warm-daemon cache.
4. **Injection-resistant selection** (§7): feature-mediated selection that never reads payload as
   instruction, generalized to diagnostic-vector classification, with an injection-versus-evasion
   account.
5. **Authority, the extraction limit, and consumer conformance** (§8, §5): authority as a
   declared record separate from evidence, a certified-set admissibility constraint grounded in a
   measured extraction limit, and **O2 (consumer conformance)** — the named, measurable obligation
   that the consumer honor the guarded reading.

We are explicit about what is *not* novel: the qualitative privacy–coverage tension is an instance
of the noninterference-versus-declassification literature [GoguenMeseguer1982; SabelfeldMyers2003;
SabelfeldSands2009; ClarksonSchneider2010]; the value of separating valid from complete answers
over inconsistent data is known [Motro1989]; treating input as untrusted structure rather than
instruction is the LangSec discipline [Sassaman2013]. Our contribution is their synthesis for
agent context plus the specific constructions, bounds, and honest scoping above.

---

## 2. Motivating Scenarios

**S1 — Silent collision (absence ≠ safety).** A developer branches to edit `ledger/rounding.go`.
An open PR already rewrites the same symbol, but the broker's view of the relevant repository is
stale (the host was briefly unreachable). A system that simply returns "no conflicts" licenses a
false sense of safety. The requirement: distinguish *no conflict observed (fresh)* from *not
observed* — and never let the second masquerade as the first.

**S2 — Authority conflict.** The linked ticket says the rounding cap is 5; a linked policy page
says 3; the code does 3. Three plausible sources disagree, and no governance rule says which is
authoritative. A system that silently picks one can be confidently wrong. The requirement: model
the conflict, refuse to adjudicate, surface it.

**S3 — Cross-permission existence leak.** An open PR touches a shared library inside a repository
the developer cannot access. Even *acknowledging* its existence leaks sensitive information. The
requirement: the observable — including its shape, size, and timing — must be invariant under
changes confined to artifacts the consumer cannot see.

**S4 — Poisoned artifact (injection).** A PR body contains text crafted to read as an instruction
to the agent. The requirement: the broker must select and present that text as *evidence*,
defanged and labeled, never as something it acts on, and its own selection must not be steerable
by treating payload as instruction.

These four requirements — coverage honesty, authority conflict, existence-privacy, and
injection-resistance — structure the formal model.

---

## 3. Related Work

**Reference monitors and information flow.** The broker is a reference monitor [Anderson1972]
mediating context release. Existence-privacy is a noninterference property [GoguenMeseguer1982];
the controlled relaxation via the dial is declassification [SabelfeldSands2009]. Both privacy and
coverage are *hyperproperties* over sets of executions [ClarksonSchneider2010], and the
privacy–coverage tension is the general noninterference-versus-completeness conflict, here
specialized. We borrow the language-based discipline of treating untrusted input as data, not
control [SabelfeldMyers2003; Sassaman2013].

**Inconsistent and incomplete data.** Separating *valid* from *complete* answers over data that
may be missing or contradictory is classical [Motro1989]; our coverage certificate and
three-valued semantics specialize this to agent context, and authority declarations play the role
of a governance-supplied resolution order over multi-source disagreement [BellLaPadula1973;
JajodiaSandhu].

**Prompt injection and agent context.** Indirect prompt injection through ingested content is a
live attack class [Perez2022; Greshake2023]. Retrieval-augmented generation [Lewis2020] addresses
recall, not coverage honesty, privacy, or injection. The Model Context Protocol [MCP2024]
standardizes transport; we standardize the *guarantees*. Object-capability principles [Miller2006]
inform the capability-by-absence packaging. Where the broker admits ephemeral caches, their
staleness is reported rather than hidden, in the spirit of bounded-staleness and conflict-free
replication [Shapiro2011].

**Three-valued reasoning.** The typed `Unknown` is Kleene's strong three-valued logic [Kleene1952]
put to an operational use: the broker's consumer rule is a sound under-approximation that returns
`Unknown` rather than risk a false `False`.

---

## 4. Formal Model

A **subject** `s ∈ S` is any unit about which a scoped claim can be made (a changed path, a
symbol, a linked ticket/doc, a review gate). An **observation** is
`O = (s, source, t, payload, fidelity, completeness)`: a normalized fact about `s` from a named
`source` at time `t`, with a fidelity tag (faithfulness of normalization) and a completeness tag
(whether it suffices for a deterministic comparison).

The **evidence state** summarizes observations of `s`:
```
E(s) ∈ { fresh, stale, partial, missing, unreachable, unsupported }.
```
`fresh` = current comparable evidence within the freshness window; `stale` = exists but past the
window; `partial` = present but insufficient for a deterministic comparison (also the state a
source-count shortfall forces — §5); `missing` = expected but not collected; `unreachable` =
collection attempted and failed; `unsupported` = subject known but not modeled or collectable.

The broker `B` is a **deterministic, side-effect-free** function of its inputs (current source
state, configuration, declarations, and a clock value passed explicitly): no I/O, randomness, or
hidden state in its core; collection and transport are separate, untrusted-at-the-boundary
layers. `B` produces a pair
```
B(⋯) = ⟨ C, κ ⟩
```
where `C` is the **certified card set** and `κ` is the **coverage certificate**.

**The fixed-envelope certificate.** `κ` is emitted in a **constant shape** determined only by the
consumer-visible scope: every in-scope source family and every in-scope subject appears, with
`Unknown[unobserved]` as filler for anything not observed. Thus `|κ|` and its structure are a
function of the `P`-visible scope alone — never of whether some invisible artifact happens to
exist (the privacy consequence is Theorem 5). `κ` carries per-source evidence states, per-§8
authority states, a per-subject δ-gated dependency-closure status (§5), and a **snapshot
reference** (Theorem 1).

**The hint layer and its projection invariant.** A separate, explicitly **untrusted hint layer**
`H` may carry best-effort guesses. `H` never enters `C` and carries no certificate weight. Define
the **consumer projection** `Π_P(·)` that drops every element whose witness source is not
`P`-visible. The model imposes:

> **I-H (hint projection).** Every surfacing path emits `Π_P(H)`, never raw `H`. Projection is the
> *only* exposed form of `H`, so `H` can never reintroduce an invisible-existence channel.

The **consumer** is the agent (or human surface); it holds only `⟨C, κ⟩` (and optionally
`Π_P(H)`), never the broker's internal state.

**Theorem 1 (Determinism / verifiable, TTL-bounded replay).** For fixed inputs (source snapshot,
configuration, declarations, clock), `B` yields identical `⟨C, κ⟩`. `κ` carries a snapshot
reference `{ digest, snapshot_id, ttl }`: the signed `digest` **binds** the inputs permanently
(it always *verifies* a claimed replay), and the broker **retains the content-addressed snapshot
for the bounded window `ttl`**, during which a verifier can **re-derive `⟨C, κ⟩` and confirm the
binding**. After `ttl` the snapshot is garbage-collected; the digest still verifies a replay
presented to it but can no longer reconstitute one. *Sketch:* `B`'s core is pure and all
nondeterminism (time, collection) is lifted to explicit inputs recorded in / referenced by `κ`;
retention is a bounded side table outside the trusted core, keyed by `snapshot_id`. ∎

---

## 5. Guarded Semantics and Observable Soundness

We want the consumer to reason soundly about propositions over work-state (e.g. "no open PR
conflicts with my changed paths") without the broker ever asserting falsity or invisible
existence — and we want to be exact about the *scope* of that soundness.

**Dependency closure — an explicit object.** For a proposition `ρ`, `deps_G(ρ) ⊆ Σ` is the set of
sources whose state can affect `ρ`, generated from (i) typed references reachable from `ρ`'s
subject, (ii) policy-mandated sources for `ρ`'s scope, and (iii) the query structure. `deps_G` is
part of the **trusted rule set**, and its correctness is the load-bearing obligation. We split it
into a part the broker can *enforce* and a part it can only *measure* — and we do not pretend the
second is the first.

> **O1a (no undeclared emission) — enforced, every request.** A connector declares a reference
> schema enumerating the reference classes it can emit. On *every* request, each reference a
> connector actually emits is checked against that schema; any class emitted-but-undeclared forces
> `complete?` to `incomplete[unmodeled-ref]` — **never `complete`** — and is recorded in `κ`. The
> runtime check (not just a deploy-time gate) catches a connector that *drifts* — emits a new
> class after its manifest was vetted — so a drifted or buggy class degrades to `Unknown`, never a
> false `False`.
>
> **O1b (declared-class recall) — measured, not proven.** O1a guarantees the connector emits
> nothing it did not declare; O1b is the converse, harder claim: that it emits *every instance* of
> its declared classes that the source actually contains. This is a **recall** property and is
> **not machine-decidable in general** — you cannot see what you failed to extract. It is bounded
> two ways, neither a proof: (i) a **per-connector reference-recall bar `ρ`** — each connector
> must clear recall ≥ `ρ` on an audited adversarial reference corpus (the dual of the value
> *precision* bar `τ`, §8); and (ii) **source-count cross-checks** — where a source reports a count
> or manifest for a reference class (a PR's changed-file count, an issue's link count), the
> connector compares emitted-vs-reported and forces `incomplete[partial]` on a shortfall,
> converting part of O1b into a runtime invariant for the classes a source can count.

**Completeness checker — the certificate object.** Define a *total*
`complete? : (Prop, κ) → {complete} ∪ {incomplete[r]}`:
```
complete                  every σ∈deps_G(ρ) is in κ with E(source σ)=fresh, and deps_G(ρ) is closed
incomplete[dangling]      a typed reference reachable from ρ has an unobserved target (E∈{missing,unreachable,partial})
incomplete[stale-dep]     some σ∈deps_G(ρ) is present but E(source σ)≠fresh
incomplete[partial]       a source-count cross-check (O1b-ii) shows the connector emitted fewer than the source reports
incomplete[policy-gap]    a policy-mandated source for ρ's scope is absent or non-fresh in κ
incomplete[unbounded]     ρ's closure hits a connector schema flagged unbounded, or a depth-bounded traversal is truncated
incomplete[unmodeled-ref] a connector emitted a reference class deps_G does not model (O1a)
```
`incomplete[unbounded]` is a syntactic/bounded check, never a semantic "is this set finite?"; so
`complete?` is genuinely total. `κ` carries the per-subject closure status `complete?` consumes,
so the consumer **runs `complete?` itself**.

**Closure status is δ-gated.** `complete?` is evaluated over the consumer projection `Δ_P`, and the
closure status published in `κ` is filtered by the per-subject dial `δ_s` (§6). A dangling
reference whose *target* is `P`-invisible is reported as a generic `Unknown[unobserved]` under
`δ_s=none`; the precise reason is declassified only at higher `δ_s`.

**Meta-theoretic valuation (oracle view).** Let `witness(c)` map a card to the propositions it
establishes; a card witnessing `π` establishes `π` and refutes `¬π`. Relative to an omniscient
oracle:
```
⟦ρ⟧ = Unknown[conflicting-evidence]  if cards witness BOTH ρ and ¬ρ
⟦ρ⟧ = True   if a card witnesses ρ,   or  (ρ universal   ∧ complete?(ρ,κ)=complete ∧ no card witnesses ¬ρ)
⟦ρ⟧ = False  if a card witnesses ¬ρ,  or  (ρ existential ∧ complete?(ρ,κ)=complete ∧ no card witnesses ρ)
⟦ρ⟧ = Unknown[reason]   otherwise
```
An *existential* `ρ` is `True` by one witness, `False` only by exhaustive absence; a *universal*
`ρ` is `False` by one counterexample, `True` only by exhaustive absence. Contradictory witnesses
resolve to `Unknown[conflicting-evidence]`, distinct from §8's authority `conflicted`.

**The broker emits no valuation.** `B` outputs only `⟨C, κ⟩`; it never computes `⟦ρ⟧`. Were `B`
to emit `⟦ρ⟧`, adding a consumer-invisible source to `deps_G(ρ)` would flip `False → Unknown`, a
value-channel signal of invisible existence. Keeping `⟦·⟧` meta-theoretic closes that channel by
construction.

**Sound consumer rule.** A consumer holding `⟨C, κ⟩` evaluates `⟦·⟧⁻` by the same shape-branched
rule, running `complete?` against `κ` and carrying its failure tag into `Unknown[reason]`.

**Theorem 2 (Observable soundness, relative to `deps_G`).** *Under O1a, and assuming O1b over the
typed-reference world,* `⟦ρ⟧⁻ = True ⇒ ⟦ρ⟧ = True` and `⟦ρ⟧⁻ = False ⇒ ⟦ρ⟧ = False` **with respect
to the dependency closure `deps_G` models** — the consumer never over-claims over those
dependencies; it may only under-claim. *Sketch:* `True` holds by a witness (Theorem 3) or, for a
universal, by exhaustive absence under `complete?`; `False` dually. `complete?=complete` requires
every modeled dependency observed `fresh` and the closure gap-free, and O1a (runtime-audited)
guarantees no emitted dependency is silently outside the schema, so the oracle's checker agrees
*on the modeled closure*. ∎

> **Scope — stated, not hidden.** `complete?` certifies completeness **over the typed closure**,
> not over reality. A true dependency that flows only through an **unmodeled channel** — e.g. a
> free-text reference (A1) — is invisible to `deps_G`; a `complete` verdict can therefore be wrong
> there, a false `complete` and hence a possible false `True`/`False`. **O1a cannot catch this**
> (nothing undeclared was emitted; something real was simply never extracted), and **O1b only
> bounds it** within the typed world (recall ≥ `ρ`, source-count cross-checks). The residual is
> exactly the **relevance ceiling** (E2: structural relevance ≈ 38% of behaviour-changing events).
> So the honest claim is *soundness over a modeled closure, with measured recall, over a
> named-incomplete world* — strictly weaker than, and more truthful than, "never over-claims."

**Theorem 3 (No fabrication).** Every `c ∈ C` is witnessed by ≥1 observation in `κ` with a recorded
source and time. *Sketch:* card construction is a total function of observations; cards carry their
witness set, checkable against `κ`. ∎

**Theorem 4 (Foreign-key observable soundness).** If a subject is reachable only through a reference
whose target source is unobserved (`E ∈ {missing, unreachable, partial}`), the dangling reference
is reported in `κ`; the consumer's `⟦·⟧⁻` yields `Unknown[unobserved]`, never `False`. *Sketch:*
`deps_G` includes reference targets, so an unobserved target makes `complete?` return
`incomplete[dangling]`. ∎

**O2 (consumer conformance) — a named, measurable obligation.** The broker proves `⟨C, κ⟩` is sound
(Theorem 2) and emits no valuation; the *benefit* — that absence never licenses "clear" — is
realized only if the consumer applies `⟦·⟧⁻` and treats `Unknown` as not-clear. The broker cannot
enforce this on a downstream model. O2 is therefore an obligation on the consumer, and — unlike the
trusted-base assumptions — it is **directly measurable** (§9, E5): give agents `κ` and measure
whether they avoid false-clears. Soundness of the observable is the broker's to prove; conformance
to it is the consumer's to demonstrate.

---

## 6. Existence-Privacy, the Per-Subject Dial, and Side-Channel Discipline

Let a consumer `P` have a visibility predicate `can_read(P, ·)`. Partition artifacts into
`P`-visible and `P`-invisible.

**Theorem 5 (Existence-privacy, including shape and size).** With the dial set to `none` for a
subject `s` (`δ_s = none`), the broker's observable `⟨C, κ⟩` restricted to `s` — **including the
certificate's shape and size** — is invariant under any change confined to `P`-invisible
artifacts. *Sketch:* `C` is selected only from `P`-visible observations; `B` emits no valuation
whose value depends on invisible existence; the **fixed-envelope** `κ` (§4) has shape/size a
function of the `P`-visible scope alone, with invisible-target gaps masked to `Unknown[unobserved]`
by the δ-gate. Hence two states differing only in invisible artifacts induce identical observables
for `s`, byte-shape included. ∎ (Resolving S3: the cross-permission PR is neither surfaced, hinted
— by I-H, `H` is exposed only as `Π_P(H)` — nor inferable from how big or how shaped the
certificate is.)

**The per-subject dial.** Declassification is controlled **per subject (or per scope)** by a map
`δ : S → {none, count, identity}`. `δ_s` governs disclosure of *invisible-target dangling
references for `s`*: `none` reveals nothing; `count` reveals how many; `identity` reveals which. An
operator can hold `δ_s = none` over sensitive scopes while allowing `δ_s = count` over benign ones.
Default is `none` everywhere.

**Theorem 6 (Privacy–coverage impossibility; qualitative).** Define **EP**: the observable is
invariant under changes to `P`-invisible artifacts; **CC**: for every globally-relevant unobserved
source, `κ` reports its existence. *If a globally-relevant `P`-invisible source can exist, EP and CC
are jointly unsatisfiable.* *Sketch:* construct `S` with such a `σ` and `S' = S∖{σ}`; invisibility
gives `S|_P = S'|_P`, while CC forces the observables to differ, contradicting EP. ∎ Not claimed as
novel.

**Theorem 6′ (Single-shot leakage bound, per subject).** Fix `s` and an adversary-known candidate
set of `M_s` invisible-target dangling references; let `X_s ∈ {0,1}^{M_s}` be their presence
vector. Over a single invocation (timing and certificate-shape excluded by the discipline below),
the mutual information between `X_s` and the observable is `0 / ≤ log₂(M_s+1) / ≤ M_s` bits for
`δ_s = none / count / identity`. *Sketch:* data-processing over the deterministic map; ranges
`1, M_s+1, ≤2^{M_s}`. ∎

**Theorem 6″ (Multi-query leakage bound — single-snapshot).** *For a fixed source snapshot*, over
any adaptive query sequence (timing and certificate-shape excluded by the discipline below), let
`Q` be the distinct subjects queried and `X_Q` their joint invisible secret. Then
`I(X_Q ; transcript) ≤ Σ_{s∈Q} I_s`, the sum of per-subject single-shot bounds; **re-querying a
subject adds nothing**. *Sketch:* `B` is deterministic with no per-call randomness, so the whole
transcript is a fixed function `g(X_Q, public)`; data-processing and subadditivity give the sum,
and repeated identical queries map to identical responses (zero marginal entropy); adaptivity
cannot exceed the range. ∎ **Scope:** the bound is **per snapshot**. Across snapshots the secret
evolves, and the temporal channel below is *not* covered — bounding adaptive multi-query against a
*changing* world is open.

**Side-channel discipline (a requirement, not a non-goal).** Theorem 5 covers the observable's
value, shape, and size; a deployment must also keep its *timing* from leaking, and must not let
operational markers reopen the channel.
- **Fixed-envelope certificate (§4).** Closes the certificate-shape/size channel **by
  construction**: `|κ|` and structure depend on the `P`-visible scope only (Theorem 5).
- **Timing-invariance via the warm daemon.** The latency design (§9, E1) *is* the timing
  mitigation: answers are constant-time reads from a freshness-stamped cache over the `P`-visible
  projection, and cache-fill is a background, request-independent process. Per-request timing is
  therefore invariant to invisible existence, **provided the cache-fill schedule is not
  adversary-controlled per request** (a stated discipline). Existence-privacy and the latency
  design are the same mechanism.
- **Truncation post-projection.** `Unknown[truncated]` (§8) is computed over `Δ_P`, so it signals
  visible volume only.

**Residual channels (genuinely open).** *Temporal correlation* — an adversary watching a subject's
certificate across snapshots can infer invisible activity from changes in the *visible* shape (a
card appearing when an invisible artifact merges into a visible path); the fixed envelope dampens
but does not eliminate this. *Cross-subject total volume* across a large query set. Both are stated
as open, not closed.

---

## 7. Injection-Resistant Selection

Source `payload` is **untrusted evidence, never instruction.** Selection is mediated by a **typed
extractor** `φ`: cards are chosen by typed features over observable structure, not by interpreting
payload as a command.

**Theorem 7 (Feature-mediated selection).** If selection is a function only of typed features
`φ(·)` over observable structure, no string in `payload` alters the broker's control flow or the
cards it emits *as a matter of being read as instruction*. *Sketch:* `φ` ranges over a fixed typed
feature space; payload enters only as data to `φ`. ∎ Injected instructions arrive **defanged and
labeled as evidence** (resolving S4 on the broker side; end-to-end safety still requires a
cooperating consumer — O2, §10).

**Diagnostic-vector classification.** Generalize to a vector of deterministic judges
`J(c) = (j₁,…,j_k)`, each `jᵢ ∈ {1,0,⊥}` and feature-mediated. A fixed total
`class : {1,0,⊥}^k → Class` maps the pattern to a card class (e.g. file-overlap with no
symbol-overlap ⇒ *phantom*, suppressed).

**Theorem 8 (Classification preserves injection-resistance).** If every `jᵢ` is feature-mediated
and `class` is fixed and total, no payload determines which classifier runs or is read as
instruction. *Sketch:* composition of feature-mediated judgments under a fixed total map is
feature-mediated. ∎

**Injection versus evasion.** Theorem 8 guarantees *control-flow integrity*, not *classifier
robustness*. An adversary may craft payload to deterministically set a feature (e.g. whitespace to
flip a semantic-equivalence judge) and steer the *class*. This is **evasion, not injection**,
expected and permitted; judges on open-ended features are best-effort and stay in `H`, while only
pinned/typed judges yield certified classes (§8). A full non-interference lemma is the outstanding
proof obligation.

---

## 8. Authority and the Certified-Set Constraint

**Evidence vs. authority.** Evidence answers *what is observed*; **authority** answers *what should
be true*. Authority is a **governance declaration**: `α = (scope, source, priority)`, gathered into
`Δ` out-of-band, computed over the consumer-visible projection
`Δ_P = Π_P(Δ) = { α∈Δ : can_read(P, source(α)) }` — declarations over invisible sources contribute
nothing, preserving Theorem 5.

**Pinned extraction.** All authority values come from a **pinned, typed, partial** extractor `φ_f`
over a declared schema field `f`, returning `V ∪ {⊥}`. Authority never uses open-ended extraction.

**Authority state** — a total deterministic function of `(Δ_P, E, φ)`, `A(s, P)`. Let `M(s)` be the
priority-maximal declarations in `applies_P(s)` (a *fresh* in-window temporary override outranks
steady-state; a stale/`⊥` temporary is not maximal). Freshness is source-indexed:
```
conflicted  if ≥2 α∈M(s) have E(source(α))=fresh, φ_f(source(α))≠⊥, with values differing under f's typed equality
resolved    if the unique α∈M(s) has E(source(α))=fresh and φ_f(source(α))≠⊥
missing     if applies_P(s) = ∅
Unknown[stale-authority]  if the priority-maximal authority is present but stale — a stale higher-priority authority is never silently overridden by a fresh lower-priority one
Unknown[unobserved]  otherwise (φ_f=⊥, or the maximal authority's source genuinely unobserved)
```
*Example.* `Δ_P` declares the policy page authoritative over the ticket for rounding scope. If the
policy page is **stale** and the ticket is **fresh**, `A(s,P) = Unknown[stale-authority]` ("refresh
the policy") — *not* `resolved` to the ticket, and distinct from `Unknown[unobserved]`. Silently
falling through to the fresh lower-priority source would be exactly the *absence ⇒ safety* failure
the model forbids.

Because `A` depends on `Δ_P`, it is consumer-relative; replay fixes `P`. The certificate reports the
categorical `A(s,P)` in the fixed envelope; by the projection this adds zero information about
invisible sources, preserving Theorems 5, 6′, 6″.

**Typed Unknown.** `Unknown` carries a reason — `unobserved | no_authority | conflict | truncated`
— each demanding a distinct consumer action.

**Authority-relative observable soundness.** A `resolved` value card is sound iff
`E(source(α))=fresh` and `φ_f(source(α))=v≠⊥`; a `conflicted` card is sound iff ≥2 priority-maximal
declarations have fresh, pinned-typed, divergent values — it asserts *that* they diverge, never
*which* is correct (resolving S2; `fidelity ≠ truth`).

**Demote, not suppress.** For any `(source, field)` with a fresh pinned-typed value diverging from
the resolved authority, a representation must exist in `C` (a *dissent* card, using the *same*
validated `φ_f`) or in `H`. When the volume budget cannot hold every distinct divergence, omitted
ones are surfaced as `Unknown[truncated]` in `κ` — computed over `Δ_P` (§6) so it signals visible
volume only. Agreement carries no information and may be suppressed.

**Certified-set admissibility (a design constraint).** A claim is admitted to `C` only if it is (i)
**extraction-free structural**, or (ii) a **pinned-typed comparison** where `φ_f` is *validated*
(deterministic, schema-bounded, returns `⊥` on out-of-schema input, clears a precision bar `τ` on an
adversarial conformance suite) and licensed by a declaration in `Δ_P` or the resolved authority of
`s`. All other value-(dis)agreement claims are inadmissible to `C` and may appear only in `H`. The
bar `τ` (value precision) and the bar `ρ` (reference recall, §5/O1b) are the two measured
gatekeepers of the certified surface — one for *what a value is*, one for *whether a reference was
seen*. This constraint is **deliberately conservative, not complete**, grounded in §9's extraction
limit.

---

## 9. Evaluation

The evaluations are **characterizations and stress tests**, not estimates of how often these
conditions occur in production. Where a number is quoted it is measured on an archived corpus;
where a metric is defined but not yet measured under audit, that is said plainly. Baselines are
named for each. Corpora and the replay harness are archived with the paper.

**E1 — The latency of honesty (and timing-invariance).** A naive design re-verifying every source
per request approximates a sum/max of source tail-latencies; over four modeled cloud sources ≈ 4 s
p95 (serial) / ≈ 2.5 s (parallel). A **warm-daemon design** with freshness-stamped,
background-refreshed caches reduces per-request latency to a cache read (≈ 8 ms p95), moving the
cost to *staleness*, which `κ` reports. The same mechanism delivers the §6 timing-invariance: a
constant-time cache read over the `P`-visible projection does not vary with invisible existence. So
"deterministic and honest" need not mean slow, "stateless" means *no durable trusted state* (not
*no cache*, and — with Theorem 1 — not *no bounded replay buffer*), and the cache is a privacy
control as much as a performance one.

**E2 — Coverage of structural relevance.** On an adversarially-generated corpus of high-value
work-start events (three independent frontier-model generators, self-classified), purely
*structural* relevance accounts for ≈ 38% of events; learned/semantic ≈ 43%; declared-policy ≈ 18%.
*Baseline:* against an LLM-retrieval recall pass on the same corpus, the structural slice is the
certifiable, highest-confidence, costliest-to-miss subset — recall the LLM may match or exceed, but
without coverage honesty, privacy, or injection-resistance. This supports certifying the structural
core, routing learned guesses to `H`, and letting declared authority grow the certified fraction
(the "Unknown ⇒ write it down" flywheel). It is also the concrete statement of the §5 relevance
ceiling: ≈ 62% of behaviour-changing context flows through non-structural channels a `complete`
verdict makes no claim about.

**E3 — The extraction limit (grounding the §8 `τ` bar).** On a 48-item adversarial corpus of
linked-artifact pairs (representation, superseded-section, unit, free-text traps), two deterministic
disagreement detectors reached **precision 0.44** (false positives concentrated in representation
and superseded-section traps; free-text recall 0). *Baseline:* far below an LLM-judge on the easy
cases, but the LLM-judge is non-deterministic and unbounded — inadmissible to a *certified* surface.
This is the empirical basis for excluding undeclared, open-extraction value-disagreement from `C`.
Revisiting requires clearing `τ` on an independently-audited adversarial corpus.

**E4 — The price of soundness (false-`Unknown`).** Soundness (Theorem 2) is purchased with
*under-claim*: the consumer returns `Unknown` wherever it cannot prove `True`/`False`. **Method:**
on a labeled corpus where the oracle valuation is known, replay against a fixed snapshot and compute
the **false-`Unknown` rate** — the fraction of propositions with `⟦ρ⟧ ∈ {True,False}` for which
`⟦ρ⟧⁻ = Unknown` — stratified by `incomplete[·]` cause and by whether a declaration was present.
**Two facts hold by construction:** the false-`False`/false-`True` rate is **0** over the modeled
closure (Theorem 2) — soundness is not a tunable, only the `Unknown` rate moves — and the
false-`Unknown` rate is **lower-bounded by the undeclared non-structural share** (≈ the E2 learned
slice, ~43%), shrinking toward that floor as declarations and freshness grow. *Baseline:* the value
E4 buys is the *false-clear* rate it prevents — a no-coverage retrieval baseline's rate of calling
an unobserved subject "clear." **We report the metric definition and these two bounds; the point
measurement comes from the archived conformance corpus and is a characterization, not a
production-frequency estimate. No headline false-`Unknown` number is quoted here because none has
yet been measured under audit** — stating the metric and its proven bounds, not inventing a value,
is the position consistent with this paper's bar.

**E5 — Consumer conformance (does the honest signal get honored?).** O2 (§5) is measurable.
**Method:** present agents with `κ` and measure the **false-clear rate** — how often an agent
proceeds as "clear" on a subject the certificate marks `Unknown` — against a baseline of agents
given the same task without `κ`. Preliminary agent-consumption probes (archived) indicate that
surfacing gated context changes agent behaviour; a calibrated, audited false-clear measurement is
the standing obligation, reported the same way as E4 — defined and bounded here, not quoted as a
number we have not measured.

---

## 10. Assumptions and Limitations

**Assumptions.** (A1) Only typed/linked artifacts propagate; implicit/free-text references are out
of scope for `C` (this is the residual named in §5's soundness scope). (A2) A single logical
sequencer orders ingestion. (A3) Metadata is trustworthy where sources cannot sign it. (A4) `φ` is
robust **only** for validated, pinned, typed fields. (A5) Connector permission mirroring reflects
true ACLs. (A6) Declarations `Δ` are authentic governance input. (A7) Authority is computed over
`Δ_P`.

**Trusted-base and conformance obligations.**
- **(O1a)** no undeclared emission — *enforced* by a per-request runtime audit against each
  connector's schema; a drifted/undeclared class degrades to `Unknown`, never a false `False`.
- **(O1b)** declared-class recall — *measured, not proven*: a per-connector recall bar `ρ` on an
  audited corpus, plus source-count cross-checks forcing `incomplete[partial]` on shortfall.
- **(O2)** consumer conformance — the consumer must honor `⟦·⟧⁻` and treat `Unknown` as not-clear;
  *measurable* (E5), not broker-enforceable.
Theorem 2 is stated **relative to the typed closure `deps_G`** under O1a + O1b; the unmodeled /
free-text residual (the relevance ceiling, E2) is a place a `complete` verdict can be wrong, and is
bounded by O1b within the typed world but not eliminated.

**Side channels.** The certificate-shape/size channel is **closed by construction** (fixed
envelope, Theorem 5) and per-request timing is **invariant** under the warm-daemon discipline
(§6/E1). **Open:** temporal correlation across snapshots, and cross-subject total volume; the
multi-query bound (Theorem 6″) is single-snapshot.

**Other limitations.** *Fidelity ≠ truth.* *Relevance ceiling:* unwritten/unlinked knowledge is not
captured (the `H` layer may guess, uncertified, and only ever as `Π_P(H)`). *End-to-end injection
safety needs a cooperating consumer.* *Undeclared open-extraction disagreement is out of `C`* by
measurement (§9). *Replay is TTL-bounded* (Theorem 1). *Proof obligations:* the Theorem-8
non-interference lemma, a mechanized artifact (Theorems 1, 2, 5, 6″), and the audited O1b recall,
E4, and E5 measurements are future work; this paper offers rigorous sketches and defined,
bounded metrics.

---

## 11. Conclusion

teamctx treats context for AI agents as an *assurance* problem rather than a retrieval problem. By
removing the language model from the core and emitting only a certified card set and a coverage
certificate — never a truth valuation — the broker proves observable soundness **over the
dependencies it models**, is precise about the world that model does not cover, preserves
existence-privacy across permission boundaries down to the certificate's shape, timing, and size,
bounds the leakage of its per-subject dial single-shot and per-snapshot, resists injection by
treating source text as evidence rather than instruction, and separates governance authority from
observed evidence so conflict is surfaced rather than resolved. Determinism does triple duty: it
makes answers verifiable by replay, caps how much an adversary learns no matter how many times they
ask within a snapshot, and — through the warm cache — makes response time itself reveal nothing. Its
honesty is the point, and v1.2's discipline is to be equally honest about the honesty's *limits*:
the trusted base is a measured-recall closure, the consumer must cooperate, and a temporal observer
is not yet bounded. The result is a context layer a security reviewer can approve *because* it is
deterministic, read-only, incapable-by-construction of retaining or fabricating, and explicit about
its own edges — and that an agent can rely on *because* absence never masquerades as safety.

---

## References

- [Anderson1972] J. P. Anderson. *Computer Security Technology Planning Study.* 1972.
- [GoguenMeseguer1982] J. Goguen, J. Meseguer. *Security Policies and Security Models.* IEEE S&P, 1982.
- [SabelfeldMyers2003] A. Sabelfeld, A. Myers. *Language-Based Information-Flow Security.* IEEE JSAC, 2003.
- [SabelfeldSands2009] A. Sabelfeld, D. Sands. *Declassification: Dimensions and Principles.* J. Computer Security, 2009.
- [ClarksonSchneider2010] M. Clarkson, F. Schneider. *Hyperproperties.* J. Computer Security, 2010.
- [BellLaPadula1973] D. Bell, L. LaPadula. *Secure Computer Systems.* 1973.
- [JajodiaSandhu] S. Jajodia, R. Sandhu. *Toward a Multilevel Secure Relational Data Model.* ACM SIGMOD, 1991.
- [Motro1989] A. Motro. *Integrity = Validity + Completeness.* ACM TODS, 1989.
- [Kleene1952] S. C. Kleene. *Introduction to Metamathematics.* 1952.
- [Sassaman2013] L. Sassaman, M. Patterson, S. Bratus, et al. *The Halting Problems of Network Stack Insecurity.* ;login:, 2011/2013.
- [Perez2022] F. Perez, I. Ribeiro. *Ignore Previous Prompt: Attack Techniques for Language Models.* 2022.
- [Greshake2023] K. Greshake, et al. *Not What You've Signed Up For: Compromising Real-World LLM-Integrated Applications with Indirect Prompt Injection.* AISec, 2023.
- [Lewis2020] P. Lewis, et al. *Retrieval-Augmented Generation for Knowledge-Intensive NLP Tasks.* NeurIPS, 2020.
- [Shapiro2011] M. Shapiro, N. Preguiça, C. Baquero, M. Zawirski. *Conflict-Free Replicated Data Types.* SSS, 2011.
- [Miller2006] M. Miller. *Robust Composition.* PhD thesis, 2006.
- [MCP2024] Anthropic. *Model Context Protocol.* Specification, 2024.

---

## Appendix A — Certificate Schema and a Worked Trace

**A.1 Schema (typed records).**
```
Card := {
  kind     : collision | authority_conflict | superseded | gate | dissent | fyi
  subject  : SubjectRef
  claim    : Prop
  witness  : [ObsRef]                   -- Theorem 3: no card without witness
  severity : { value: 0..1, kind_base, magnitude_norm, scope_mult }
  judges   : { name: 1 | 0 | ⊥ }        -- Theorem 8
  tier     : certified | hint
  why      : string
}

κ := {                                  -- FIXED ENVELOPE: shape/size are a function of the P-visible scope only
  snapshot_ref : { digest: signed-hash, snapshot_id: content-address, ttl: window }   -- Theorem 1
  sources      : { source_id: { E: fresh | stale⟨age⟩ | partial⟨emitted/reported⟩ | unreachable | missing | unsupported } }
  authority    : { subject: resolved⟨α,v⟩ | missing | conflicted⟨αs⟩ | temporary⟨α,expiry⟩ | unknown[unobserved | stale-authority] }
  closure      : { prop_id: complete | incomplete[ dangling | stale-dep | partial | policy-gap | unbounded | unmodeled-ref ] }  -- δ_s-gated
  delta        : { subject: none | count | identity }   -- per-subject dial
}
```
Every in-scope source/subject is present (with `Unknown[unobserved]` filler), so the certificate's
shape leaks nothing about invisible existence (Theorem 5). A consumer evaluates `⟦ρ⟧⁻` purely from
`⟨C, κ⟩` and must honor `Unknown` (O2).

**A.2 Worked trace (ledger rounding; S1 + S2, with an O1b cross-check).**

*Inputs `(subject, source, t, …, E)`:*
```
O1  rounding.Apply        github:PR!4471   fresh             -- open PR rewrites the symbol
O2  JIRA-2231 cap          jira             fresh  v=5        -- linked ticket
O3  "Rounding Policy"      confluence       stale⟨2d⟩ v=3     -- linked doc, DECLARED authoritative
O4  shared-proto MR        gitlab           unreachable       -- linked proto dep; host down
O5  PR!4471 changed files  github           partial⟨7/9⟩      -- source reports 9 changed files; connector emitted 7 (O1b-ii cross-check)
Δ_P : { rounding-scope → (confluence "Rounding Policy", priority HIGH) }
δ   : { rounding-scope → none }
```

*Valuations:*
```
ρ1 = "no open PR conflicts with rounding.Apply"   (universal)
     O1 witnesses a conflict (¬ρ1) ⇒ ⟦ρ1⟧⁻ = False, certified, BY COUNTEREXAMPLE.
     Exhaustiveness: gitlab(shared-proto) unreachable ⇒ incomplete[dangling]; AND github changed-files
     emitted 7 of 9 ⇒ incomplete[partial] (O1b cross-check) — the conflict set's completeness is Unknown
     for an honest, source-confirmed reason, not a guess.  (S1.)

ρ2 = "the authoritative rounding cap is v"
     M = { Rounding Policy (HIGH) }, E(confluence)=stale ⇒ A = Unknown[stale-authority]  (refresh the policy).  (S2.)
```

*Emitted `κ` (fixed envelope):*
```
sources  : { github: partial⟨7/9⟩, jira: fresh, confluence: stale⟨2d⟩, gitlab: unreachable }
authority: { rounding-cap: unknown[stale-authority] }
closure  : { ρ1: False-by-counterexample; exhaustiveness incomplete[partial]+incomplete[dangling],
             ρ2: incomplete[stale-dep] }
delta    : { rounding-scope: none }
snapshot_ref : { digest: …, snapshot_id: …, ttl: 7d }
```

*Consumer result (honoring O2):* a **certified collision** (ρ1 False — act on it), with
exhaustiveness **Unknown** for two source-grounded reasons (a host is down; the connector saw
fewer files than GitHub reports it changed) — so "nothing else surfaced" is never read as clear; and
an **authoritative-cap-unverifiable** card tagged `stale-authority` (refresh the policy), distinct
from "no authority configured." No value fabricated; no stale source passed as fresh; no invisible
source leaked — in value, shape, size, or timing; and the one place a model could have guessed (cap
= the fresh ticket's 5) it instead surfaced the staleness. `κ.snapshot_ref` lets a reviewer replay
it verbatim for 7 days. Every guarantee of §§5–8 is exercised in one request — including the O1b
cross-check that turned a silent under-collection into an explicit `partial`.
