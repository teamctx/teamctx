# Honest Context: A Deterministic Broker with Observable Soundness, Existence-Privacy, and Injection-Resistant Selection for AI Coding Agents

*Protocol paper, v1.1 — a clean, self-contained treatment. It states the model, theorems,
and evaluation in full; it is not written as a diff against any prior draft. Relative to the
v1.0 line it adopts the 2026-06-19 tightening pass natively: a **runtime** discharge of the
`deps_G` obligation, a **canonical hint-projection invariant**, a **retrievable, TTL-bounded
snapshot** for replay, a **per-subject** declassification dial, a **multi-query** leakage
bound, and an evaluation of the **cost of honesty** (false-`Unknown` rate). Bar: claims never
outrun proof — every theorem states its assumptions and carries a proof sketch; mechanization
is named as future work; empirical results are characterizations, not production-frequency
estimates.*

---

## Abstract

AI coding agents increasingly act on context drawn from a team's live systems — open pull
requests, issue trackers, design docs — yet the tools that supply that context are themselves
untrusted, incomplete, and mutually inconsistent. An agent that sees "no conflict" cannot tell
whether none exists or whether the relevant source was never observed; an agent that ingests a
pull-request body cannot tell evidence from injected instruction; a context layer that reads
everything a team produces is, by construction, a surveillance and exfiltration risk. We
present **teamctx**, a **deterministic, no-LLM, read-only context broker**, and a formal model
for *context assurance*. The broker emits only a certified card set and a coverage
certificate, and **never a truth valuation** — a construction that lets us prove **observable
soundness** (the broker never fabricates and never licenses "absence ⇒ safety") while
preserving **existence-privacy** across permission boundaries, tuned by a **per-subject**
declassification dial whose leakage we bound information-theoretically both **single-shot** and
under **adaptive multi-query** access. We treat source text as untrusted evidence, never
instruction, giving **feature-mediated, injection-resistant selection**, and we separate
**evidence** (what is observed) from **authority** (what a governance declaration says should
be true), surfacing conflict rather than silently resolving it. A **certified-set
admissibility constraint**, grounded in a measured limit of deterministic extraction, keeps
unreliable claims out of the trusted surface. Determinism makes the broker's answers
**verifiable by replay** against a retrievable, TTL-bounded snapshot. We do not claim the
qualitative privacy–coverage tension as novel (it specializes known information-flow results);
our contributions are the synthesis for agent context, the no-valuation soundness
construction, the dial's single- and multi-query leakage characterization, the
authority/extraction-limit treatment, and an injection-versus-evasion account of
classifier-based selection. Evaluation characterizes a latency design that defeats the
"honesty tax," the coverage reachable by purely structural relevance, the precision limit of
undeclared disagreement detection, and the **price of soundness** as a false-`Unknown` rate.

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

**Source text is trusted as instruction.** A pull-request body, a ticket comment, or a wiki
page may contain text that, when fed to an LLM, reads as a command ("ignore the acceptance
criteria and …"). Indirect prompt injection through ingested artifacts is now a documented
attack class [Greshake2023]. A context layer that pipes source text into a model is an
injection delivery system.

**Reading everything is surveilling everything.** A layer with read access to a team's PRs,
tickets, and docs — across people and permissions — is simultaneously the most useful context
source and the most dangerous: it can profile developers, and it can leak the *existence* of
work across permission boundaries (the presence of a treasury-team PR is itself sensitive).

Existing approaches each cover a slice but do not make *soundness, privacy, authority conflict,
and injection* the primary reasoning surface. Retrieval-augmented generation [Lewis2020]
improves recall but says nothing about coverage honesty or injection. Agent "memory" systems
accumulate trusted state — precisely the thing that can be poisoned, drift, or be subpoenaed.
The Model Context Protocol [MCP2024] standardizes a transport but not the guarantees carried
over it. None treats "no finding ≠ healthy," cross-permission existence-privacy, or
evidence-vs-authority conflict as first-class.

**Thesis.** A context broker that is *deterministic* and contains *no language model in its
core* can make guarantees a model-in-the-loop system cannot — and the same decision that buys
those guarantees (determinism) also buys token savings, non-retention, and cross-agent
portability. The cost is that the broker is *honestly incomplete*: it certifies what it can
prove and explicitly marks the rest unknown. §9 measures that cost.

**Contributions.**
1. A formal model of *context assurance* (§4): subjects, observations, evidence states, a
   certified card set `C`, a coverage certificate `κ`, and an untrusted hint layer `H` subject
   to a **canonical projection invariant**, over a deterministic, side-effect-free core whose
   answers are **verifiable by replay** against a retrievable, TTL-bounded snapshot.
2. **Observable soundness via a no-valuation construction** (§5): the broker emits only
   `⟨C, κ⟩` and never a truth valuation, so a sound consumer under-approximates a three-valued
   semantics without the broker ever signalling falsity or invisible existence. We prove
   no-fabrication and foreign-key soundness, and discharge the dependency-closure obligation
   **at runtime**, not only at deployment.
3. **Existence-privacy with a per-subject declassification dial** (§6): a privacy property
   across permission boundaries, a qualitative privacy–coverage impossibility (specialized from
   known results), a **single-shot** mutual-information bound, and a **multi-query** bound that
   determinism makes finite.
4. **Injection-resistant selection** (§7): feature-mediated selection that never reads payload
   as instruction, generalized to diagnostic-vector classification, with an explicit
   *injection-versus-evasion* account.
5. **Authority and the extraction limit** (§8): authority as a declared record separate from
   evidence, with a `conflicted` state and authority-relative soundness; and a **certified-set
   admissibility constraint** grounded in a measured limit of deterministic extraction (§9).

We are explicit about what is *not* novel: the qualitative privacy–coverage tension is an
instance of the noninterference-versus-declassification literature [GoguenMeseguer1982;
SabelfeldMyers2003; SabelfeldSands2009; ClarksonSchneider2010]; the value of separating valid
from complete answers over inconsistent data is known [Motro1989]; treating input as untrusted
structure rather than instruction is the LangSec discipline [Sassaman2013]. Our contribution is
their synthesis for agent context plus the specific constructions and bounds above.

---

## 2. Motivating Scenarios

**S1 — Silent collision (absence ≠ safety).** A developer branches to edit
`ledger/rounding.go`. An open PR already rewrites the same symbol, but the broker's view of the
relevant repository is stale (the host was briefly unreachable). A system that simply returns
"no conflicts" licenses a false sense of safety. The requirement: distinguish *no conflict
observed (fresh)* from *not observed* — and never let the second masquerade as the first.

**S2 — Authority conflict.** The linked ticket says the rounding cap is 5; a linked policy page
says 3; the code does 3. Three plausible sources disagree, and no governance rule says which is
authoritative. A system that silently picks one can be confidently wrong. The requirement:
model the conflict, refuse to adjudicate, surface it.

**S3 — Cross-permission existence leak.** An open PR touches a shared library inside a
repository the developer cannot access. Even *acknowledging* its existence leaks sensitive
information. The requirement: the observable must be invariant under changes confined to
artifacts the consumer cannot see.

**S4 — Poisoned artifact (injection).** A PR body contains text crafted to read as an
instruction to the agent. The requirement: the broker must select and present that text as
*evidence*, defanged and labeled, never as something it acts on, and its own selection must not
be steerable by treating payload as instruction.

These four requirements — coverage honesty, authority conflict, existence-privacy, and
injection-resistance — structure the formal model.

---

## 3. Related Work

**Reference monitors and information flow.** The broker is a reference monitor [Anderson1972]
mediating context release. Existence-privacy is a noninterference property [GoguenMeseguer1982];
the controlled relaxation via the dial is declassification [SabelfeldSands2009]. Both privacy
and coverage are *hyperproperties* of the broker's behavior over sets of executions
[ClarksonSchneider2010], and the privacy–coverage tension is the general
noninterference-versus-completeness conflict, here specialized. We borrow the language-based
discipline of treating untrusted input as data, not control [SabelfeldMyers2003; Sassaman2013].

**Inconsistent and incomplete data.** Separating *valid* from *complete* answers over data that
may be missing or contradictory is classical [Motro1989]; our coverage certificate and
three-valued semantics specialize this to agent context, and authority declarations play the
role of a governance-supplied resolution order over multi-source disagreement, related to
multilevel and policy-mediated views [BellLaPadula1973; JajodiaSandhu].

**Prompt injection and agent context.** Indirect prompt injection through ingested content is a
live attack class [Perez2022; Greshake2023]. Retrieval-augmented generation [Lewis2020]
addresses recall, not coverage honesty, privacy, or injection. The Model Context Protocol
[MCP2024] standardizes transport; we standardize the *guarantees*. Object-capability principles
[Miller2006] inform the capability-by-absence packaging (a read-only artifact cannot write).
Where the broker admits ephemeral caches, their staleness is reported rather than hidden, in
the spirit of bounded-staleness and conflict-free replication [Shapiro2011].

**Three-valued reasoning.** The typed `Unknown` is Kleene's strong three-valued logic
[Kleene1952] put to an operational use: the broker's consumer rule is a sound
under-approximation that returns `Unknown` rather than risk a false `False`.

---

## 4. Formal Model

A **subject** `s ∈ S` is any unit about which a scoped claim can be made (a changed path, a
symbol, a linked ticket/doc, a review gate). An **observation** is
`O = (s, source, t, payload, fidelity, completeness)`: a normalized fact about `s` from a named
`source` at time `t`, with a fidelity tag (faithfulness of normalization) and a completeness
tag (whether the observation suffices for a deterministic comparison).

The **evidence state** summarizes observations of `s`:
```
E(s) ∈ { fresh, stale, partial, missing, unreachable, unsupported }.
```
`fresh` = current comparable evidence within the freshness window; `stale` = exists but past
the window; `partial` = present but insufficient for a deterministic comparison; `missing` =
expected but not collected; `unreachable` = collection attempted and failed; `unsupported` =
subject known but not modeled or collectable.

The broker `B` is a **deterministic, side-effect-free** function of its inputs (current source
state, configuration, declarations, and a clock value passed explicitly): it performs no I/O,
randomness, or hidden state in its core; collection and transport are separate,
untrusted-at-the-boundary layers. `B` produces a pair
```
B(⋯) = ⟨ C, κ ⟩
```
where `C` is the **certified card set** (typed claims the broker will stand behind), and `κ` is
the **coverage certificate**: per-source evidence states, per-§8 authority states, a
per-subject **dependency-closure status** (§5, δ-gated), and a **snapshot reference** —
discussed under Theorem 1 — that lets a verifier check, and within a bounded window re-derive, a
past `⟨C, κ⟩`.

**The hint layer and its projection invariant.** A separate, explicitly **untrusted hint
layer** `H` may carry best-effort guesses (e.g. a learned relevance hunch). `H` never enters
`C` and carries no certificate weight. Define the **consumer projection**
`Π_P(·)` that drops every element whose witness source is not `P`-visible (the same projection
that yields `Δ_P` in §6/§8). The model imposes a **canonical projection invariant**:

> **I-H (hint projection).** Every surfacing path emits `Π_P(H)`, never raw `H`. Projection is
> not conditional on "if surfaced" — it is the *only* exposed form of `H`. Hence `H` is outside
> the `⟨C, κ⟩` privacy contract yet can never reintroduce an invisible-existence channel,
> because no un-projected hint is observable.

The **consumer** is the agent (or human surface); it holds only `⟨C, κ⟩` (and optionally
`Π_P(H)`), never the broker's internal state.

**Theorem 1 (Determinism / verifiable, TTL-bounded replay).** For fixed inputs (source
snapshot, configuration, declarations, clock), `B` yields identical `⟨C, κ⟩`. `κ` carries a
**snapshot reference** `{ digest, snapshot_id, ttl }`: the signed `digest` **binds** the inputs
permanently (it always *verifies* a claimed replay), and the broker **retains the
content-addressed snapshot for the bounded window `ttl`**, during which a verifier can
**re-derive `⟨C, κ⟩` and confirm the binding**. After `ttl` the snapshot is garbage-collected;
the digest still verifies a replay presented to it but can no longer reconstitute one. The TTL
makes replay operationally real within the window while bounding retention — consistent with
the no-durable-trusted-state stance (§9, E1). *Sketch:* `B`'s core is a pure function and all
nondeterminism (time, collection) is lifted to explicit inputs recorded in / referenced by
`κ`; retention is a bounded side table outside the trusted core, keyed by `snapshot_id`. ∎

---

## 5. Guarded Semantics and Observable Soundness

We want the consumer to reason soundly about propositions over work-state (e.g. "no open PR
conflicts with my changed paths") without the broker ever asserting falsity or invisible
existence.

**Dependency closure — an explicit object, not an adjective.** For a proposition `ρ`,
`deps_G(ρ) ⊆ Σ` is the set of sources whose state can affect `ρ`, generated from (i) typed
references reachable from `ρ`'s subject in the global graph, (ii) policy-mandated sources for
`ρ`'s scope, and (iii) the query structure. `deps_G` is part of the **trusted rule set**, and
its correctness is a *named obligation*, discharged at deployment **and continuously at
runtime**:

> **O1 (`deps_G` soundness — an explicit assumption with a runtime discharge).** A connector
> provides *local structural completeness*: its declared reference schema enumerates every
> reference class it can emit. O1 is the **assumption** that local structural completeness
> composes to a global over-approximation of `ρ`'s true dependencies — an honest trusted-base
> assumption, not a proof. It is *enforced* on two fronts. (a) **Deployment gate:** the broker
> validates each connector's schema manifest before admitting it. (b) **Runtime audit:** on
> *every* request, each observation a connector emits is checked against that connector's
> declared schema; any reference class actually emitted but not declared makes `complete?`
> return `incomplete[unmodeled-ref]` for the affected closure — **never `complete`** — and
> records the offending class in `κ`. The runtime audit closes the gap between deploys: a
> connector that *drifts* (emits a new class after its manifest was vetted) degrades to
> `Unknown` immediately, rather than silently certifying against a stale manifest until the next
> deployment. So an undeclared, buggy, or drifted class degrades to `Unknown`, never a false
> `False`.

**Completeness checker — the certificate object.** Define a *total* function
`complete? : (Prop, κ) → {complete} ∪ {incomplete[r]}` with enumerated failure modes:
```
complete                  every σ∈deps_G(ρ) is in κ with E(source σ)=fresh, and deps_G(ρ) is closed
incomplete[dangling]      a typed reference reachable from ρ has an unobserved target (E∈{missing,unreachable,partial})
incomplete[stale-dep]     some σ∈deps_G(ρ) is present but E(source σ)≠fresh
incomplete[policy-gap]    a policy-mandated source for ρ's scope is absent or non-fresh in κ
incomplete[unbounded]     ρ's closure hits a connector schema flagged unbounded, or a depth-bounded traversal is truncated
incomplete[unmodeled-ref] a connector emitted a reference class deps_G does not model (O1: deploy gate or runtime audit)
```
`incomplete[unbounded]` is a **syntactic/bounded** check — a schema flag or a truncated
depth-bounded traversal — **never** a semantic decision of "is this set finite?" (which would
be undecidable over free-text refs); so `complete?` is genuinely total. `κ` carries the
per-subject dependency-closure status that `complete?` consumes, so the consumer **runs
`complete?` itself**; completeness is *checked against an object*, never asserted by adjective.

**Closure status is δ-gated (privacy — closing a leak the certificate could otherwise
introduce).** `complete?` is evaluated over the consumer projection `Δ_P`, and the closure
status published in `κ` is filtered by the per-subject dial `δ_s` (§6). A dangling reference
whose *target* is `P`-invisible must not expose its existence: under `δ_s = none` such a case is
reported as a **generic `Unknown[unobserved]`** — the `[dangling]` reason and any count are
withheld; the precise reason is declassified only at higher `δ_s` (§6). Thus
`incomplete[dangling]` in `κ` denotes a *visible*-target gap; invisible-target gaps are masked,
so the per-subject closure status cannot reopen T5/T6 or bypass the dial.

**Meta-theoretic valuation (oracle view).** Let `witness(c)` map a card to the propositions it
establishes; a card witnessing `π` establishes `π` **and refutes `¬π`**. `True` and `False` are
**dual under proposition shape**: a single witness settles the *easy* polarity, the *hard*
polarity needs exhaustive absence. Relative to an omniscient oracle:
```
⟦ρ⟧ = Unknown[conflicting-evidence]  if cards witness BOTH ρ and ¬ρ
⟦ρ⟧ = True   if a card witnesses ρ,   or  (ρ universal   ∧ complete?(ρ,κ)=complete ∧ no card witnesses ¬ρ)
⟦ρ⟧ = False  if a card witnesses ¬ρ,  or  (ρ existential ∧ complete?(ρ,κ)=complete ∧ no card witnesses ρ)
⟦ρ⟧ = Unknown[reason]   otherwise   (reason = complete?'s incomplete[·] tag, or §8's authority reasons)
```
So an *existential* `ρ` is `True` by one witness and `False` only by exhaustive absence; a
*universal* `ρ` is `False` by one counterexample and `True` only by exhaustive absence of any
counterexample (this symmetry is what makes a true universal like Appendix A's `ρ₁` evaluate
correctly — a single-witness-`True`-only scheme would wrongly call it `False`). Contradictory
witnesses resolve to `Unknown[conflicting-evidence]` — never `True ∧ False`, preserving Theorem
2 — and are **distinct** from §8's authority `conflicted` (which is declared-value
disagreement, not contradictory observed facts).

**The broker emits no valuation.** `B` outputs only `⟨C, κ⟩`; it never computes or transmits
`⟦ρ⟧`. This is essential: were `B` to emit `⟦ρ⟧` at runtime, adding a consumer-invisible source
to `deps_G(ρ)` would flip `False → Unknown`, a value-channel signal of invisible existence —
exactly the leak §6 forbids. Keeping `⟦·⟧` meta-theoretic closes that channel by construction.

**Sound consumer rule.** A consumer holding `⟨C, κ⟩` evaluates `⟦·⟧⁻` by the same
shape-branched rule: `Unknown[conflicting-evidence]` if cards witness both `ρ` and `¬ρ`; else
`True` if a card witnesses `ρ` or (`ρ` universal ∧ `complete?(ρ,κ)=complete` ∧ no card
witnesses `¬ρ`); `False` if a card witnesses `¬ρ` or (`ρ` existential ∧ `complete?=complete` ∧
no card witnesses `ρ`); otherwise `Unknown[reason]`, carrying `complete?`'s failure tag.

**Theorem 2 (Observable soundness).** *Under O1,* `⟦ρ⟧⁻ = True ⇒ ⟦ρ⟧ = True` and
`⟦ρ⟧⁻ = False ⇒ ⟦ρ⟧ = False`; the consumer never over-claims (it may only under-claim,
returning `Unknown` where the oracle would say `True`/`False`). *Sketch:* `True` holds by a
witness (Theorem 3 ⇒ `ρ` holds) or, for a universal, by exhaustive absence of a counterexample
under `complete?`+O1. `False` holds by a counterexample (Theorem 3 ⇒ `¬ρ` holds) or, for an
existential, by exhaustive absence under `complete?`+O1. `complete?=complete` requires every
dependency observed `fresh` and the closure gap-free, and by O1 — now enforced per request by
the runtime audit, so it holds against the *actual* emitted schema, not a stale manifest — the
consumer's `deps_G` misses no true dependency, so the oracle's checker agrees. Contradictory
witnesses give `Unknown`, never an over-claim; every other case is `Unknown`. ∎ The rigor rests
on **O1 (a checkable per-connector assumption, discharged at deploy and at runtime) and the
total `complete?` checker** — not the word "conservative." Standing obligation: `Unknown ≠
False` — absence never licenses "clear" (resolving S1).

**Theorem 3 (No fabrication).** Every `c ∈ C` is witnessed by at least one observation in `κ`
with a recorded source and time; `B` emits no card without supporting evidence. *Sketch:* card
construction is a total function of observations; cards carry their witness set, checkable
against `κ`. ∎

**Theorem 4 (Foreign-key observable soundness).** If a subject is reachable only through a
reference whose target source is unobserved (`E ∈ {missing, unreachable, partial}`), the
dangling reference is reported in `κ` as such; the consumer's `⟦·⟧⁻` therefore yields
`Unknown[unobserved]`, never `False`, for propositions depending on it. *Sketch:* `deps_G`
includes reference targets, so an unobserved target makes `complete?` return
`incomplete[dangling]`, forcing `Unknown[unobserved]`. ∎

---

## 6. Existence-Privacy and the Per-Subject Declassification Dial

Let a consumer `P` have a visibility predicate `can_read(P, ·)` over sources. Partition
artifacts into `P`-visible and `P`-invisible.

**Theorem 5 (Existence-privacy).** With the dial set to `none` for a subject `s` (`δ_s = none`),
the broker's observable `⟨C, κ⟩` restricted to `s` is invariant under any change confined to
`P`-invisible artifacts. *Sketch:* `C` is selected only from `P`-visible observations, and (by
§5) `B` emits no valuation whose value depends on invisible existence; `κ` reports states only
for `P`-visible sources, and `s`'s closure status is `δ_s`-gated. Hence two states differing
only in invisible artifacts induce identical observables for `s`. ∎ (Resolving S3: the
cross-permission PR is neither surfaced nor hinted — by I-H, `H` is exposed only as `Π_P(H)`,
so the hint path cannot reintroduce the channel Theorem 5 closes for `⟨C, κ⟩`.)

**The per-subject dial.** Declassification is controlled **per subject (or per scope)** by a
map `δ : S → {none, count, identity}`, not a single global setting. `δ_s` governs disclosure of
*invisible-target dangling references for `s`*: `none` reveals nothing; `count` reveals how many
invisible-target references exist; `identity` reveals which. An operator can hold `δ_s = none`
over sensitive scopes (e.g. a security repo) while allowing `δ_s = count` over benign ones,
trading privacy for coverage **where it is safe to**, rather than all-or-nothing. The default is
`none` everywhere.

**Theorem 6 (Privacy–coverage impossibility; qualitative).** Define **EP**: the observable is
invariant under changes to `P`-invisible artifacts; **CC**: for every globally-relevant
unobserved source, `κ` reports its existence. *If a globally-relevant `P`-invisible source can
exist, EP and CC are jointly unsatisfiable.* *Sketch:* construct `S` with such a source `σ` and
`S' = S∖{σ}`; invisibility gives `S|_P = S'|_P`, while CC forces the observables to differ,
contradicting EP. ∎ This is the noninterference-versus-completeness tension [SabelfeldSands2009;
ClarksonSchneider2010] specialized to agent context; the qualitative result is *not* claimed as
novel.

**Theorem 6′ (Single-shot leakage bound, per subject).** Fix a subject `s` and an
adversary-known candidate set of `M_s` potential invisible-target dangling references for `s`;
let the secret `X_s ∈ {0,1}^{M_s}` be their presence vector, with an arbitrary prior. Over a
*single* invocation, with timing and cross-call correlation excluded, the mutual information
between `X_s` and the observable `δ_s(D(q))` is: `δ_s=none`: `I = 0`; `δ_s=count`:
`I ≤ log₂(M_s+1)`; `δ_s=identity`: `I ≤ M_s` bits. *Sketch:* data-processing over the
deterministic map `X_s ↦ obs`; `H(f(X_s)) ≤ log₂|range(f)|` with ranges `1, M_s+1, ≤2^{M_s}`. ∎

**Theorem 6″ (Multi-query leakage bound).** Consider an adversary issuing any adaptive sequence
of queries `q₁,…,q_n` (each over some subject), excluding timing and certificate-size channels.
Let `Q ⊆ S` be the set of *distinct* subjects queried and `X_Q = (X_s)_{s∈Q}` the joint
invisible-presence secret over them. Then the mutual information between `X_Q` and the entire
transcript is bounded by the **sum of per-subject single-shot bounds**:
```
I(X_Q ; transcript)  ≤  Σ_{s∈Q} I_s ,     where  I_s = 0 / log₂(M_s+1) / M_s   for δ_s = none / count / identity.
```
In particular, re-querying a subject yields **no additional leakage**. *Sketch:* because `B` is
deterministic with no per-call randomness or hidden state, every response is a fixed function of
the (fixed) inputs; the whole transcript is therefore a deterministic function
`g(X_Q, public)`. By data-processing and subadditivity of entropy,
`I(X_Q;transcript) ≤ H(g(X_Q,·)) ≤ Σ_{s∈Q} log₂|range(δ_s∘D)|`, which is the stated sum;
adaptivity cannot exceed it because the adversary's later queries are themselves functions of
already-counted observables, and repeated identical queries map to identical responses
(zero marginal entropy). ∎ Thus determinism — the same property that yields verifiable replay —
also *caps* multi-query leakage at what the per-subject dials expose, with no amplification from
volume. **Out of scope (open):** timing side-channels, certificate-size channels, and leakage
across *correlated* secrets (when `X_s` are a priori dependent, the sum bound still holds but
may be loose).

---

## 7. Injection-Resistant Selection

Source `payload` is **untrusted evidence, never instruction.** Selection is mediated by a
**typed extractor** `φ`: cards are chosen by typed features computed over observable structure,
not by interpreting payload as a command or prompt.

**Theorem 7 (Feature-mediated selection).** If selection is a function only of typed features
`φ(·)` over observable structure, then no string in `payload` alters the broker's control flow
or the cards it emits as a matter of being *read as instruction*. *Sketch:* `φ` ranges over a
fixed typed feature space; payload enters only as data to `φ`, never as code. ∎ Consequently
injected instructions arrive **defanged and labeled as evidence** (resolving S4 on the broker
side; end-to-end safety still requires a cooperating consumer — §10).

**Diagnostic-vector classification.** Generalize single-feature selection to a vector of
deterministic judges `J(c) = (j₁,…,j_k)`, each `jᵢ ∈ {1, 0, ⊥}` (no-problem / problem /
no-opinion) and each itself feature-mediated. A fixed total classifier
`class : {1,0,⊥}^k → Class` maps the *pattern* to a card class (e.g. file-overlap with no
symbol-overlap ⇒ *phantom*, suppressed; whitespace-only doc change ⇒ *phantom*).

**Theorem 8 (Classification preserves injection-resistance).** If every `jᵢ` is feature-mediated
and `class` is fixed and total, then no payload determines *which* classifier runs or is read as
instruction. *Sketch:* composition of feature-mediated judgments under a fixed total map is
feature-mediated; determinism follows. ∎

**Injection versus evasion.** Theorem 8 guarantees *control-flow integrity*, not *classifier
robustness*. An adversary may craft payload to deterministically set a feature (e.g. add
whitespace to flip a semantic-equivalence judge) and thereby steer the *class*. This is **input
selection (evasion), not injection**, and is expected and permitted; its consequence is that
judges relying on open-ended/free-text features are best-effort and stay in `H`, while only
pinned/typed judges yield certified classes (§8). A full non-interference lemma — each `jᵢ` a
pure function of `φ` over observable structure with no payload-directed control flow — is the
outstanding proof obligation.

---

## 8. Authority and the Certified-Set Constraint

**Evidence vs. authority.** Evidence answers *what is observed*; **authority** answers *what
should be true*. Authority is a **governance declaration, not an inferred fact**:
`α = (scope, source, priority)`, gathered into a declaration set `Δ` supplied out-of-band.
Crucially, authority is computed over the **consumer-visible projection**
`Δ_P = Π_P(Δ) = { α∈Δ : can_read(P, source(α)) }`; declarations over invisible sources
contribute nothing to the consumer's authority state — preserving Theorem 5.

**Pinned extraction.** All authority values are obtained via a **pinned, typed, partial**
extractor `φ_f` over a declared schema field `f`, returning `V ∪ {⊥}` (`⊥` = out-of-schema /
failure). Authority never uses open-ended extraction.

**Authority state** — a total deterministic function of `(Δ_P, E, φ)`, written `A(s, P)`. Let
`M(s)` be the **priority-maximal** declarations in `applies_P(s)` (by static priority; a *fresh*
in-window temporary override outranks steady-state, a stale/`⊥` temporary is not maximal).
Freshness is indexed by source — `E(source(α))`:
```
conflicted  if ≥2 α∈M(s) have E(source(α))=fresh, φ_f(source(α))≠⊥, with values differing under f's typed equality
resolved    if the unique α∈M(s) has E(source(α))=fresh and φ_f(source(α))≠⊥
missing     if applies_P(s) = ∅
Unknown[stale-authority]  if the priority-maximal authority is present but **stale** (E(source(α))≠fresh) — observed-but-outdated; a stale higher-priority authority is **never silently overridden** by a fresh lower-priority one
Unknown[unobserved]  otherwise (φ_f=⊥, or the maximal authority's source genuinely unobserved)
```
*Example (the policy-sensitive case).* `Δ_P` declares the policy page authoritative over the
ticket for rounding scope. If the policy page is **stale** and the ticket is **fresh**, then
`A(s,P) = Unknown[stale-authority]` ("authoritative source stale — refresh it") — *not*
`resolved` to the ticket, and deliberately distinct from `Unknown[unobserved]`: the difference
is operational, telling the consumer to **refresh the policy**, not to request permissions or
treat it as never-seen. Silently falling through to the fresh lower-priority source would be
exactly the *absence ⇒ safety* failure the model forbids.

`⊥` never participates in divergence. Because `A` depends on `Δ_P`, it is consumer-relative;
replay fixes the principal `P`. The certificate may report the categorical `A(s, P)`; by the
projection this adds **zero information about invisible sources** — the conflict bit over two
`P`-visible sources is a deterministic function of already-`P`-visible values — so Theorems 5,
6′, and 6″ are preserved.

**Typed Unknown.** The guarded valuation's `Unknown` carries a reason —
`unobserved | no_authority | conflict | truncated` — each demanding a distinct consumer action
(`gather | treat as unranked dissent | escalate | the omission is explicit`).

**Authority-relative observable soundness.** A `resolved` value card is sound iff
`E(source(α))=fresh` and `φ_f(source(α))=v≠⊥`; a `conflicted` card is sound iff ≥2
priority-maximal declarations have fresh, pinned-typed, divergent values — it asserts *that*
they diverge, never *which* is correct (resolving S2; `fidelity ≠ truth`).

**Demote, not suppress (a checkable property).** For any `(source, field)` with a fresh
pinned-typed value diverging from the resolved authority, a representation must exist in `C` (a
*dissent* card, if the source is pinned-typed, using the *same* validated `φ_f`) or in `H`. **No
divergence is silently suppressed:** when the volume budget cannot hold a representation of every
distinct divergence, omitted ones are surfaced as `Unknown[truncated]` in `κ` — the cap is
respected, omissions are explicit. Agreement with the resolved authority carries no information
and may be suppressed.

**Certified-set admissibility (a design constraint, not a theorem).** A claim is admitted to `C`
only if it is (i) **extraction-free structural** (a fact over explicit edges and change-state,
needing no value extraction), or (ii) a **pinned-typed comparison** where `φ_f` is *validated*
(deterministic, schema-bounded, returns `⊥` on out-of-schema input, and clears a precision bar
`τ` on an adversarial conformance suite) and the comparison is licensed by a declaration in
`Δ_P` or by the resolved authority of `s`. All other value-(dis)agreement claims — undeclared,
open-extraction comparisons — are inadmissible to `C` and may appear only in `H`. This constraint
is **deliberately conservative, not complete**, and is grounded in the measured extraction limit
of §9.

This narrows the extractor-robustness assumption: `φ` is relied upon only for validated, pinned,
typed fields; open-ended extraction is *not* assumed robust (and §9 shows it is not). The prior
structural theorems are unaffected: Theorems 7–8 select on structural features and Theorem 4
concerns reference existence — none depends on value-extraction correctness.

---

## 9. Evaluation

The evaluations are **characterizations and stress tests**, not estimates of how often these
conditions occur in production. Artifacts and corpora are archived with the paper.

**E1 — The latency of honesty.** A naive design that re-verifies every source on every request
approximates a sum/maximum of source tail-latencies; over four modeled cloud sources this is
≈ 4 s at p95 (serial) or ≈ 2.5 s (parallel). A **warm-daemon design** with freshness-stamped,
background-refreshed caches reduces per-request latency to a cache read (≈ 8 ms p95), moving the
cost to *staleness*, which `κ` reports. Hence "deterministic and honest" need not mean slow, and
"stateless" means *no durable trusted state*, not *no cache* — and, with Theorem 1's TTL
snapshot, not *no bounded replay buffer* either.

**E2 — Coverage of structural relevance.** Across an adversarially-generated corpus of
high-value work-start context events (three independent frontier-model generators,
self-classified), purely *structural* relevance — explicit edges and change-state, no learning —
accounts for ≈ 38% of events; learned/semantic ≈ 43%; declared-policy ≈ 18%. The structural
slice is the certifiable, highest-confidence, costliest-to-miss subset. This supports a design
that certifies the structural core, routes learned guesses to `H`, and lets declared authority
(and the resulting "Unknown, write it down" pressure) grow the certified fraction over time.

**E3 — The extraction limit (grounding the §8 constraint).** On a 48-item adversarial corpus of
linked-artifact pairs (with representation, superseded-section, unit, and free-text traps), two
deterministic disagreement detectors reached **precision 0.44** (false positives concentrated in
representation and superseded-section traps; free-text recall 0). Below any reasonable
certification bar, this is the empirical basis for excluding undeclared, open-extraction
value-disagreement from `C` (§8). The corpus is adversarial — appropriate for a *certification*
decision, where the failures (superseded sections, "was X now Y") are common in real artifacts —
and the detector is a reasonable approximation, not a maximal `φ`; revisiting the constraint
requires clearing `τ` on an independently-audited adversarial corpus.

**E4 — The price of soundness (false-`Unknown` characterization).** Soundness (Theorem 2) is
purchased with *under-claim*: the consumer returns `Unknown` wherever it cannot prove `True`/
`False`, even when an oracle could. E4 measures that cost directly. **Method:** on a labeled
corpus where the oracle valuation `⟦ρ⟧` is known per proposition, replay the broker against a
fixed source snapshot and compute the **false-`Unknown` rate** — the fraction of propositions
with `⟦ρ⟧ ∈ {True, False}` for which `⟦ρ⟧⁻ = Unknown` — stratified by the `incomplete[·]` cause
(`dangling`, `stale-dep`, `policy-gap`, `unmodeled-ref`, `unbounded`) and by whether a governing
declaration was present. Two properties the metric must report, by construction rather than
luck: (a) the **false-`False`/false-`True` rate is 0** under O1 (Theorem 2) — soundness is not a
tunable; only the `Unknown` rate moves; and (b) the false-`Unknown` rate is **lower-bounded by
the non-structural, undeclared share** of events (≈ the E2 learned slice that lacks a
declaration), since those route to `H`/`Unknown` by the §8 admissibility constraint, and
**upper-bounded toward that floor as declarations and freshness improve** — which makes E4 the
quantitative handle on the "Unknown ⇒ write it down" flywheel. *We report the methodology and
its two structural bounds here; the point measurement is taken on the archived conformance
corpus and is a characterization, not a production-frequency estimate.* (We deliberately do not
quote a single headline number we have not measured under audit — consistent with the paper's
bar.)

---

## 10. Assumptions and Limitations

**Assumptions.** (A1) Only typed/linked artifacts propagate; implicit/free-text references are
out of scope for `C`. (A2) A single logical sequencer orders ingestion (multi-region needs a
CRDT fold, out of scope). (A3) Metadata is trustworthy where sources cannot sign it. (A4) `φ` is
robust **only** for validated, pinned, typed fields. (A5) Connector permission mirroring
reflects true ACLs. (A6) Declarations `Δ` are authentic governance input — A6 is
governance-authenticity, *not* extraction-correctness. (A7) Authority is computed over the
consumer projection `Δ_P`.

**Trusted-base obligation.** (O1) `deps_G` soundness (§5) is an explicit assumption — that
per-connector *local structural completeness* composes to a global over-approximation of `ρ`'s
dependencies — *enforced* both by deployment-time validation of each connector's schema manifest
**and by a per-request runtime audit** of emitted-vs-declared reference classes; an undeclared,
buggy, or drifted class makes `complete?` return `incomplete[unmodeled-ref]`, so a gap degrades
to `Unknown`, never a false `False`. Theorems 2 and 4 are stated *under O1*. Closure status
published in `κ` is `δ_s`-gated so it cannot reopen T5/T6 (§5).

**Limitations.** *Fidelity ≠ truth:* the broker faithfully reports what a source says, not that
the source is correct. *Relevance ceiling:* unwritten/unlinked knowledge is not captured (the
`H` layer may guess, uncertified, and only ever as `Π_P(H)`). *End-to-end injection safety needs
a cooperating consumer:* the broker hardens its selection pipe, not the downstream model; we do
not claim "incapable of harm," only bounded, structurally-scoped guarantees. *Undeclared
open-extraction disagreement is out of `C`* by measurement (§9). *Privacy bounds cover
single-shot and adaptive multi-query (Theorems 6′, 6″) but exclude timing, certificate-size, and
a-priori-correlated-secret channels,* which remain open. *Replay is bounded:* after a snapshot's
`ttl` the digest still verifies but cannot reconstitute (Theorem 1). *Proof obligations:* the
Theorem-8 non-interference lemma and a mechanized artifact (e.g. Coq/Isabelle for Theorems 1, 2,
5, 6″) are future work; this paper offers rigorous sketches.

---

## 11. Conclusion

teamctx treats context for AI agents as an *assurance* problem rather than a retrieval problem.
By removing the language model from the core and emitting only a certified card set and a
coverage certificate — never a truth valuation — the broker proves observable soundness while
preserving existence-privacy across permission boundaries, bounds the leakage of its
per-subject declassification dial under both single-shot and adaptive multi-query access,
resists injection by treating source text as evidence rather than instruction, and separates
governance authority from observed evidence so that conflict is surfaced rather than silently
resolved. Determinism does double duty: it makes answers verifiable by replay within a bounded
window, and it caps how much an adversary can learn no matter how many times they ask. Its
honesty is the point — and §9 makes the price of that honesty (under-claim, never
over-claim) a measured quantity rather than a hand-wave. The result is a context layer a
security reviewer can approve *because* it is deterministic, read-only, and
incapable-by-construction of retaining or fabricating, and that an agent can rely on *because*
absence never masquerades as safety.

---

## References

- [Anderson1972] J. P. Anderson. *Computer Security Technology Planning Study.* 1972. (Reference monitor.)
- [GoguenMeseguer1982] J. Goguen, J. Meseguer. *Security Policies and Security Models.* IEEE S&P, 1982. (Noninterference.)
- [SabelfeldMyers2003] A. Sabelfeld, A. Myers. *Language-Based Information-Flow Security.* IEEE JSAC, 2003.
- [SabelfeldSands2009] A. Sabelfeld, D. Sands. *Declassification: Dimensions and Principles.* J. Computer Security, 2009.
- [ClarksonSchneider2010] M. Clarkson, F. Schneider. *Hyperproperties.* J. Computer Security, 2010.
- [BellLaPadula1973] D. Bell, L. LaPadula. *Secure Computer Systems.* 1973.
- [JajodiaSandhu] S. Jajodia, R. Sandhu. *Toward a Multilevel Secure Relational Data Model.* ACM SIGMOD, 1991.
- [Motro1989] A. Motro. *Integrity = Validity + Completeness.* ACM TODS, 1989.
- [Kleene1952] S. C. Kleene. *Introduction to Metamathematics.* 1952. (Three-valued logic.)
- [Sassaman2013] L. Sassaman, M. Patterson, S. Bratus, et al. *The Halting Problems of Network Stack Insecurity.* ;login:, 2011/2013. (LangSec.)
- [Perez2022] F. Perez, I. Ribeiro. *Ignore Previous Prompt: Attack Techniques for Language Models.* 2022.
- [Greshake2023] K. Greshake, et al. *Not What You've Signed Up For: Compromising Real-World LLM-Integrated Applications with Indirect Prompt Injection.* AISec, 2023.
- [Lewis2020] P. Lewis, et al. *Retrieval-Augmented Generation for Knowledge-Intensive NLP Tasks.* NeurIPS, 2020.
- [Shapiro2011] M. Shapiro, N. Preguiça, C. Baquero, M. Zawirski. *Conflict-Free Replicated Data Types.* SSS, 2011.
- [Miller2006] M. Miller. *Robust Composition: Towards a Unified Approach to Access Control and Concurrency Control.* PhD thesis, 2006. (Object-capability.)
- [MCP2024] Anthropic. *Model Context Protocol.* Specification, 2024.

---

## Appendix A — Certificate Schema and a Worked Trace

To show the protocol is *implementable*, not merely describable, we give the concrete shapes of
a card and of `κ`, then trace one scenario end to end.

**A.1 Schema (typed records).**
```
Card := {
  kind     : collision | authority_conflict | superseded | gate | dissent | fyi
  subject  : SubjectRef
  claim    : Prop                       -- the typed proposition asserted
  witness  : [ObsRef]                   -- supporting observations (Theorem 3: no card without witness)
  severity : { value: 0..1, kind_base, magnitude_norm, scope_mult }   -- decomposition retained
  judges   : { name: 1 | 0 | ⊥ }        -- the diagnostic vector (Theorem 8)
  tier     : certified | hint
  why      : string
}

κ := {
  snapshot_ref : { digest: signed-hash, snapshot_id: content-address, ttl: window }  -- Theorem 1 (verifiable, TTL-bounded replay)
  sources      : { source_id: { E: fresh | stale⟨age⟩ | partial | unreachable | missing | unsupported } }
  authority    : { subject: resolved⟨α,v⟩ | missing | conflicted⟨αs⟩ | temporary⟨α,expiry⟩ | unknown[unobserved | stale-authority] }
  closure      : { prop_id: complete | incomplete[ dangling | stale-dep | policy-gap | unbounded | unmodeled-ref ] }  -- δ_s-gated: invisible-target gaps masked to Unknown[unobserved]
  delta        : { subject: none | count | identity }   -- per-subject dial
}
```
A consumer evaluates `⟦ρ⟧⁻` purely from `⟨C, κ⟩`: `True` iff a `Card.witness` covers `ρ`;
`False` iff a `Card.witness` covers `¬ρ` (counterexample) **or** `κ.closure[ρ] = complete` with
no witness for `ρ`; else `Unknown[reason]` from the closure or authority tag.

**A.2 Worked trace (scenario: ledger rounding; combines S1 + S2).**

*Inputs (observations, as `(subject, source, t, …, E)`):*
```
O1  rounding.Apply        github:PR!4471   fresh        -- open PR rewrites the symbol the dev will call
O2  JIRA-2231 cap          jira             fresh  v=5   -- linked ticket, retry cap
O3  "Rounding Policy"      confluence       stale⟨2d⟩ v=3 -- linked doc, DECLARED authoritative for rounding scope
O4  shared-proto MR        gitlab           unreachable  -- a linked proto the symbol depends on; host down
Δ_P : { rounding-scope → (confluence "Rounding Policy", priority HIGH) }   -- visible declaration
δ   : { rounding-scope → none }   -- per-subject dial; no invisible-target reference exposed
```

*Per-proposition `complete?` and valuation:*
```
ρ1 = "no open PR conflicts with rounding.Apply"   (a *universal*)
     O1 witnesses a conflict (= ¬ρ1) ⇒ ⟦ρ1⟧⁻ = False, certified, BY COUNTEREXAMPLE
       (completeness is irrelevant for refuting a universal).
     SEPARATELY, "have all conflicts been seen?" : gitlab(shared-proto) unreachable ⇒
       complete?=incomplete[dangling] ⇒ the conflict set's EXHAUSTIVENESS is Unknown.
     So: ρ1 is False (a real conflict exists, asserted); whether more exist is Unknown —
     absence of further cards never licenses "clear".  (S1.)  [gitlab is a P-visible
     target, so the [dangling] reason is exposable; an invisible target would mask to
     Unknown[unobserved] per §5's δ_s-gate.]

ρ2 = "the authoritative rounding cap is v"
     M(rounding-scope) = { Rounding Policy (HIGH) }.  E(confluence)=stale ⇒ maximal authority present-but-stale.
     A(rounding,P) = Unknown[stale-authority]  (NOT resolved-to-ticket-v5; signal = refresh the policy).   (S2.)
```

*Emitted `C`:*
```
Card{ kind: collision, subject: rounding.Apply, claim: "PR!4471 rewrites rounding.Apply",
      witness:[O1], judges:{file:1, symbol:1}, severity:{value:.84, kind_base:.80, magnitude_norm:.6, scope_mult:1.5},
      tier: certified, why: "same-symbol overlap with an open PR" }
Card{ kind: authority (unverified), subject: rounding-cap,
      claim: "authoritative cap unverifiable: declared authority (Rounding Policy) is stale 2d — refresh it",
      witness:[O3], tier: certified, why: "priority-maximal authority stale; not overridden by the fresh ticket" }
```

*Emitted `κ`:*
```
sources  : { github: fresh, jira: fresh, confluence: stale⟨2d⟩, gitlab: unreachable }
authority: { rounding-cap: unknown[stale-authority] }
closure  : { ρ1: False-by-counterexample; exhaustiveness incomplete[dangling] (gitlab unobserved, visible target),
             ρ2: incomplete[stale-dep] (confluence authority stale) }
delta    : { rounding-scope: none }      -- no invisible-target reference exposed
snapshot_ref : { digest: …, snapshot_id: …, ttl: 7d }
```

*Consumer result:* the agent sees a **certified collision** — ρ1 ("no conflicts") is **False**,
act on it — alongside a coverage note that *further* conflicts are **Unknown** (gitlab
unobserved), so it does not read "nothing else surfaced" as clear. It sees an
**authoritative-cap-unverifiable** card tagged `stale-authority` (do not assume 5 *or* 3; the
source of truth is stale — refresh it), distinct from "no authority configured." No value was
fabricated; no stale source was passed off as fresh; no invisible source leaked; and the one
place the model *could* have guessed (cap = the fresh ticket's 5) it instead surfaced the
staleness. Every guarantee of §§5–8 is exercised in one request, and `κ.snapshot_ref` lets a
reviewer replay it verbatim for the next 7 days.
