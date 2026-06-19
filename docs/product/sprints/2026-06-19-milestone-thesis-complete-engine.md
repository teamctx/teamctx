# Milestone Roadmap — Thesis-Complete Engine

*Dated 2026-06-19. The forward build plan from "Phase 1 first vertical shipped" to a
**thesis-complete engine**: the credibility engine fully demonstrated in code. Companion
to the [protocol paper v1.0](../../research/teamctx-protocol-v1.0.md) and the
[architecture decision record](../vision/architecture-decision.md). Sequencing overview:
[build-plan.md](../../engineering/build-plan.md).*

---

## 1. The milestone

**Finish line:** the credibility engine is real in code, not prose —
- the broker emits typed, witnessed cards + an honest per-proposition coverage certificate;
- a reference consumer (`evaluate`) soundly under-approximates the three-valued semantics
  (**T2 embodied + tested**, not described);
- existence-privacy holds by construction across a principal boundary (**T5 in code**);
- the structural card-kind family is complete (collision + criteria-changed +
  doc-superseded + missed-gate), each with a live dogfood proof;
- authority *behavior* surfaces conflict and refuses to adjudicate (**pillar S2**);
- determinism is verifiable by replay (**T1**), and cards are explainable + conformance-
  comparable (structured `why`, severity decomposition).

**Explicitly not in this milestone:** no pip/README/launch; no distribution/IDE panel; no
MCP transport; no durable memory layer. Full/graduated authority (temporary-override
states, `.teamctx`→durable graduation, conflict-detection precision tuning) is deferred to
the durable-layer milestone — that durable half *is* the deferred package
([architecture-decision §1](../vision/architecture-decision.md)).

## 2. The starting reality (verified 2026-06-19)

Phase 1 shipped a working pipeline on the **Sprint-01/02 fixture-lineage model**, not the
v1.0-paper model. Concretely, in `src/teamctx/core/`:
- `ContextCard` is render-shaped (`section`, `text`, `why_this_matters`, `agent_instruction`);
- `claim` does not exist — card assertions are free text, so witnesses carry no polarity;
- `Coverage.complete` = "all sources fresh" (per-source), **not** the per-proposition
  `complete?` checker with the six `incomplete[...]` reasons;
- there is no `deps_G`, no authority, no `δ`/`Δ_P` projection, no snapshot/replay.

So Theorems T2/T3 are **not yet embodied in the types**. The first half of this milestone is
therefore a **core migration** (fixture-lineage → paper model), the second half adds the
remaining card kinds + authority behavior + replay/explainability.

The migration must **preserve** the shipped, tested safety machinery — do not regress it:
the fail-closed `PolicyDecision` validators, the visibility firewall, default-deny
`status_only` source bodies, and the reference-integrity validator.

## 3. Build-once: the seams to lock

Most of the design is evolvable and must never trigger a restart. Only four commitments are
hard to reverse; these get locked early, each frozen by a test:

1. **`claim` is a typed proposition with polarity.** A card witnesses `ρ` or `¬ρ`.
   Everything downstream (witness valuation, the consumer SDK, T2) depends on this, and it
   is the one piece expensive to retrofit. *Locked in slice 1.*
2. **`C` and `H` are structurally separate** — the privacy boundary is a type, not a flag
   on a shared collection. `H` is outside the privacy contract and projected before any
   surfacing. *Locked in slice 4.*
3. **The projection boundary** — cards pre-project to the principal-visible set; the
   certificate controlled-declassifies *internally* under `δ`. (A `build_certificate(visible_obs)`
   signature would starve the dial — only `δ=none` would be implementable.) *Locked in slice 4.*
4. **Pure / deterministic core** — no I/O, time, or randomness in the core; all
   nondeterminism lifted to explicit inputs. *Already done and guarded by the core purity test.*

## 4. Strategy: in-place strangler

Evolve `core/` in place. Introduce paper-model pieces alongside the fixture fields, migrate
one slice at a time, and delete an old field only when nothing reads it. Rationale:

- **Preserves the tested fail-closed machinery by construction** — it is never rewritten,
  only threaded through.
- **`work-start` stays green and runnable end-to-end at every slice** — the engine is
  dogfoodable throughout, so the "is this useful?" question is answered continuously, not
  deferred to the end.
- No parallel core, no permanent adapter (which would leave the theorems living in the
  adapter instead of the core).

Each slice is a finishable vertical whose handoff is **green CI** (pytest + ruff + mypy) and,
where it adds a card kind, a **live dogfood proof** against `ostinato-forge/project-foundry`
(the established recipe; PR #14 left open for re-runs).

**Dogfood early and often — the working artifact leads.** We build around something we can
*see working*, not around the paper. The paper keeps us honest; the running tool tells us if
it's useful. These are two distinct signals and neither overrides the other: **CI + the
property tests judge soundness; Edgar, using `work-start` in real work, judges usefulness.**
Concretely there is a **dogfood checkpoint after slice 3** — at that point the minimal honest
engine exists (typed claims, honest closure, a sound `evaluate`), enough to wire into real
daily coding and judge as a user before committing to the breadth slices (5–9). If it feels
hollow there, we have spent three slices, not nine. The soundness properties the paper
guarantees are differentiators (positioning #10, the credibility engine), not academic
decoration, so "build around what works" must never quietly drop them — that is what the
soundness signal is for.

## 5. Slice sequence

| # | Slice | Lands | Gate |
|---|---|---|---|
| 1 | **Typed `claim` + witness polarity** | seam #1 | work-start output unchanged; claim/polarity tests |
| 2 | **`complete?` + `κ.closure`** (coverage taxonomy) | honest closure; deps_G | per-proposition closure tests |
| 3 | **Consumer SDK `evaluate(ρ, C, κ)`** | **T2 in code** (#10) | property tests vs oracle valuation |
| 4 | **Projection boundary + C/H split + δ** | seams #2, #3; **T5 in code** | privacy-invariance property test; δ=none default |
| 5 | **`criteria-changed`** card kind | breadth | dogfood proof |
| 6 | **`doc-superseded`** card kind | breadth | dogfood proof |
| 7 | **`missed-gate`** card kind (CI check-runs) | breadth | dogfood proof |
| 8 | **Thin authority** (`.teamctx` read, `κ.authority`, refuse-to-pick) | **pillar S2** | conflict-surfacing + refuse-to-pick tests; dogfood |
| 9 | **Replay/snapshot (T1) + structured `why` (#11) + severity decomposition (#6)** | explainability/replay; conformance | replay-verification test; severity conformance fixture |

**Notes for execution.** Slice 3 deliberately precedes the card kinds: once `evaluate`
exists it becomes the correctness oracle for every later kind ("given these cards, does the
sound rule return the right three-valued answer?"), so slices 5–8 test against semantics
rather than rendered strings. Slice 4 is the heaviest; split 4a (principal/Δ_P + C/H split) /
4b (certificate δ-gating + dial) if it runs long. Slice 9's items may be pulled earlier
opportunistically (e.g. wire `snapshot_ref` when `κ` stabilizes in slice 4), but they are not
prerequisites for the card kinds.

---

## 6. Slice 1 — spec'd in full

**Goal.** Give the broker's cards a typed proposition with polarity, so a card's assertion
can be matched against a query proposition — the foundation for the consumer SDK and T2.
Migrate the existing collision derivation onto it with **zero change to `work-start`'s
rendered output**.

**What changes (in-place).**
- Introduce a typed proposition into `core/` (new `core/prop.py` or alongside the card
  model): a `Prop` carrying a `predicate` identifier, a `SubjectRef`, and typed `args`, with
  a **shape** (`universal | existential`) resolved from a small predicate registry. A card's
  `claim` is a *ground* `Prop` it asserts; the card **witnesses** that claim (positive
  polarity), which by proposition duality refutes its negation.
- Add `claim: Prop` and a polarity-bearing `witness` to the card model. The collision
  predicate (`pr_conflicts_with_path`) is existential over the changed-path subject; a
  collision card witnesses a counterexample to the universal `ρ = "no open PR conflicts with
  my changed paths"`.
- `select.derive_cards` / `_derive_collision_card` build the typed `claim` from the same
  structural overlap they already compute (no new signal needed).
- The render path becomes a **pure function of the typed claim** (`claim → rendered text`),
  rather than the derivation hand-writing prose. This keeps the human-plane property
  ("renders, never via the LLM") clean and sets up structured `why` (#11) later. The
  *output bytes of `work-start` stay identical* — the rendered card reads the same; only its
  provenance changes from free text to a typed claim run through a template.

**What is preserved (must not regress).** The fail-closed `PolicyDecision` validators, the
`_is_surfaceable` visibility gate, default-deny `status_only` bodies, and the
reference-integrity checks. Slice 1 adds a typed layer above these; it does not touch them.

**Out of scope for slice 1.** No `complete?`/closure changes (slice 2), no consumer
`evaluate` (slice 3), no projection/privacy/δ (slice 4), no new card kinds. `Prop` only needs
to be rich enough to express the collision predicate and to be matchable by polarity — do not
over-build the predicate algebra now.

**Definition of done.**
- Collision cards carry a typed `claim` (ground `Prop`) and a polarity-bearing witness.
- A new test asserts the collision card witnesses `¬ρ` for the universal "no conflict" query
  (the polarity is correct — the trap the paper flags, where a single-witness scheme would
  misvalue a universal, is covered).
- `work-start`'s rendered output is byte-identical to before (a golden test guards this).
- Full gate green: pytest + ruff + mypy. No regression in the 109 existing tests.

**Why this is the right first move.** It is the one seam that is both foundational (slices
2–9 ride on it) and expensive to retrofit, and it can be landed without changing observable
behavior — the safest possible way to start an in-place migration.

---

## 7. Non-goals / deferred (named, not hidden)

- pip/PyPI, README-for-users, landing page, any launch work.
- Distribution: MCP transport, IDE panel, default-agent-invocation wiring.
- Durable memory layer (the Ambara-inheriting package) and full/graduated authority.
- Severity *calibration* (the default values) — deferred by nature, needs deployment
  telemetry. Slice 9 ships the *decomposition + conformance fixture*, not calibrated weights.
- The protocol-tightening pass reviewed 2026-06-19 (runtime O1 audit, canonical H→Δ_P
  projection, snapshot retrievable+ttl, multi-query leakage analysis, per-subject δ, false-
  Unknown eval) is **not yet written into the paper**; fold the adopted items into a v1.1
  revision separately from this build.
