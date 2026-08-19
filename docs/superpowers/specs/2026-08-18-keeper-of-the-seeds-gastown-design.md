# Keeper of the Seeds: contributing teamctx to gastown

Date: 2026-08-18 (rewritten 2026-08-19 after adversarial review)
Status: Design, pending review. No build approved yet.

## Summary

Contribute teamctx to gastown as a tool called the Keeper of the Seeds. The
Keeper is a deterministic, read-only verifier. When a gastown agent inherits
structured claims from a dead predecessor, or when the Witness is about to write
a "Verified" line, the Keeper checks those claims against git and Beads and
returns, per claim, verified, contradicted, or unconfirmed. It never asserts a
claim it cannot corroborate against an independent source.

This serves both goals we set:

- Distribution: teamctx ships as an MCP (Model Context Protocol) server plus a
  small CLI, so the generic core is reusable and gastown is the first adapter.
- Proof: gastown is a live multi-agent coding system where acting on stale
  inherited claims causes real bad actions, so it is where we measure whether
  deterministic re-checking prevents them.

This document was rewritten after an adversarial review found that the first
version assumed an insertion point gastown does not have and treated agent-written
state as ground truth. Both are corrected below.

## Objective

The Keeper optimizes one thing: the total cost to reach a verified, accepted
outcome, without reducing the requested scope, security, evidence, or quality
bar. Total cost includes model cost, failed attempts, rework, human review time,
and the cost of defects that escape.

The Keeper reduces that cost by catching stale inherited claims before an agent
acts on them. It must never reduce cost by asserting a claim it did not
corroborate. It does not manufacture a "tokens saved" number. It reports what it
checked, honestly.

## Background

teamctx is a deterministic, no-LLM, read-only context broker. It surfaces
verified facts and refuses to assert what it cannot check. Its north star is
reality-grounding.

gastown is a multi-agent orchestration system in Go. It coordinates coding
agents (Claude Code, Copilot, Codex, Gemini, and others) across projects. Work
is stored as structured data (Beads in Dolt, a version-controlled database).
Every action is attributed to an actor. Agents are Polecats: persistent
identity, ephemeral sessions. Handoff and Seance carry context from a finished
session to the next one.

## The gap, stated honestly

gastown is not defenseless against stale inherited context. The Witness verifies
a Polecat's completion before signaling merge. The Refinery re-verifies by
running tests during the merge, and has explicit paths (MERGE_FAILED,
REWORK_REQUEST) for when a "Verified" line was wrong. The mail protocol tells
agents directly that the next session should discover state from Beads, not from
mail. gastown's core principle NDI (Nondeterministic Idempotence) is built on
re-derivation and eventual consistency.

So the gap is narrow and specific: agents sometimes act on an inherited claim
instead of re-deriving it, and the one actor that writes verification claims by
hand, the Witness, is an LLM doing a deterministic job. This is a behavior gap,
not a missing subsystem. The Keeper's honest value is automating the
re-derivation an agent should already do, more cheaply and more reliably than the
agent running `bd show` and `git log` itself, and giving the Witness a
deterministic check instead of a hand-written assertion.

The design must beat the cheapest alternative, which is a one-line instruction:
"re-derive state from Beads and git before trusting a handoff claim." The Keeper
earns its place only if it catches drift that instruction misses, or catches it
at lower total cost. The proof below is built to test exactly that.

## What the Keeper is

The Keeper is a tool, not a gastown role. gastown roles (Mayor, Deacon, Witness,
Polecat) are LLM agents with sessions, identities, and hooks. A deterministic
Python service is not that. gastown's own integration guidance steers external
components toward presets, hooks, and the `gt` CLI, and away from internals, and
states that integration is configuration, not compilation. The Keeper follows
that guidance.

The name still fits. The seeds are the verified claims, the real stock carried
across the death of a session. The Keeper hands forward only what it can vouch
for and labels the rest. What changed from the first draft is the delivery: a
tool the Witness and agents call, not a new first-class role.

First consumer: the Witness. The Witness already composes "Verified" lines by
hand. Giving it a deterministic check to call before it writes those lines is the
highest-value insertion point, because it replaces an unreliable LLM assertion
with a checked one at the exact place the claim is created.

## Scope

In scope for v1:

- Verify the structured key-value fields of inherited messages. HANDOFF and
  MERGE_READY carry fields such as Issue, Branch, MR, and Exit. The Keeper checks
  these against git and Beads and returns a status per field.
- Serve the Witness. Expose the same check as an MCP tool the Witness calls
  before composing a "Verified" line.
- Label freeform recollection. The freeform sections of a handoff cannot be
  verified deterministically. They get one blanket label: unverified
  recollection, re-derive before acting. The Keeper does not pretend to check
  them claim by claim.

Out of scope:

- Extracting factual claims from freeform prose. teamctx is no-LLM, so this is
  not possible deterministically, and v1 does not attempt it.
- Intercepting or replacing inherited text. gastown injects raw recollection
  through its own code (`gt mail check --inject`) and Seance spawns a live
  subprocess. The Keeper cannot remove that text. It appends a receipt beside it.
- Seance verification. There is no seam between a Seance answer and the agent, so
  v1 does not try to verify Seance content.
- Writing to any gastown store, work decomposition, routing, lifecycle, typed
  mail routing, storage, and attribution. gastown does these.

## Verification model

This is the core of the Keeper. It decides what counts as verified.

### Trust tiers by author path

A source's tier is set by who produced it, not by which store holds it or which
message type carries it.

- Tier 0: produced by a deterministic process, not an agent. Git state (commits,
  branches, merge status, file presence at a ref) and CI artifacts.
- Tier 1: attributed, structured, but written by an agent. Beads records (issue
  status, bead state), and agent-composed mail such as the Witness's "Verified"
  line. Only POLECAT_DONE is tool-generated; treat the rest of mail as Tier 1.
- Tier 2: freeform recollection from an agent, including Handoff prose and Seance
  answers.

### The corroboration and independence rule

A claim is verified only when an independent Tier 0 source confirms it. A Tier 1
record does not verify a claim when the same agent wrote both the claim and the
record as part of the same work. A Polecat closing its own bead and then writing
"issue closed" in its handoff is one assertion made twice, not a claim and its
confirmation. The Keeper confirms "issue closed" against git and merge state, or
it returns unconfirmed.

This follows gastown's own principle: reality is truth, state is derived. Beads
is derived state, so it is evidence, not ground truth.

### The result contract (frozen)

Each checked claim returns one of:

- verified: an independent Tier 0 source confirms it.
- contradicted: a Tier 0 source disagrees with it. This is the highest-value
  result, because it is the one that stops a bad action.
- unconfirmed: no independent source could confirm or contradict it.

Separately, if the Keeper itself cannot run (store unreachable, timeout, error),
it returns verification_unavailable. This is a distinct signal, never folded into
unconfirmed. An agent must be able to tell "I checked and could not confirm" from
"I could not check."

Every result carries the source checked, its tier, and provenance pinned to the
exact git SHA and Dolt commit read. The shape (status, tier, source, pinned
provenance, receipt) is frozen as v1 and guarded by a test that fails on drift.
Changing it requires a superseding decision record landed with the test update.

### True as of pin, not true now

A verified claim is a snapshot. gastown's merge queue and patrol loops mutate
state constantly, so a claim can be true at the read and false a second later.
The Keeper does not claim "true now." Every result states the git SHA and Dolt
commit it was read at, so the reader knows exactly what the verification is
relative to. For volatile git facts the honest freshness window is near zero, so
the design does not lean on cache reuse of these facts.

### One pure decision core

Both callers (the hook that checks an inherited message, and the Witness calling
before it writes a claim) run through one pure, deterministic function. Same
inputs give the same result, and it performs no I/O. Reads happen outside it and
are passed in as tier-labeled evidence. The two callers cannot diverge on what
counts as verified.

## Behavioral contract

A status is useless unless the agent does something with it. gastown's ZFC
principle leaves the decision to the agent, so this is guidance injected with the
receipt, not enforcement:

- verified: proceed.
- contradicted: stop and re-derive before acting.
- unconfirmed: re-derive the claim before acting on it.
- verification_unavailable: treat as unconfirmed. It is not a pass.

Whether the status actually changes the agent's next action is the first thing
the proof measures.

## Architecture and integration

teamctx stays in Python. gastown is in Go. They do not share code. The Keeper
runs as its own process and exposes two surfaces: a CLI and an MCP tool.

Realistic data flow (corrected from the first draft):

1. The user adds a hook command alongside gastown's own, for example
   `teamctx verify-handoff` after `gt mail check --inject`.
2. gastown injects the raw inherited message as it does today. The Keeper does
   not remove it.
3. The Keeper parses only the structured fields, reads git and Beads read-only,
   runs the pure decision core, and appends a compact receipt to the agent's
   context beside the raw text: per field, a status with source, tier, and pinned
   provenance, plus the behavioral contract.
4. Separately, the Witness calls the Keeper as an MCP tool before composing a
   "Verified" line, and writes the checked result instead of a hand assertion.

Reads: git through normal git commands, Beads through the `bd` CLI. No direct
Dolt access. Read-only throughout.

Claim schema: because Polecats work in isolated worktrees and rigs have an
integration branch, every claim carries the repo, worktree, and ref it is checked
against. "Git state" without a ref is ambiguous.

Latency: the hook is the hot path, so the Keeper call is best-effort with a hard
timeout modeled on gastown's own sub-second prime budget. On timeout or error it
returns verification_unavailable and the agent keeps working. The Keeper never
blocks an agent and never sits in a blocking position.

MCP surface (spec 2026-07-28, verified separately): stateless, which costs
teamctx nothing because it holds no session state. The verification result is
returned through the frozen contract above. The earlier pitch about cache hints
as an edge is dropped, because the most valuable facts here are the most volatile.

## Efficiency and viability

- Fail open, with outage as its own signal. On any Keeper failure the agent
  keeps working, and the failure is reported as verification_unavailable, never
  as a silent unconfirmed and never as a pass.
- Off the blocking path. Deterministic local reads, best-effort with a timeout,
  no model call anywhere.
- Sparse and quiet. The receipt is capped and covers only the structured fields.
  Nothing is emitted when there is nothing to check.

Deferred as viability items, not v1: signal-triggered revalidation (it needs a
daemon watching gastown events, which contradicts the stateless, off-path
design), and any background process.

## Security and data boundary

- Credentials by reference only. If a store needs auth, credentials are named by
  reference and resolved at runtime by trusted code. They never enter results,
  receipts, or logs.
- Receipt boundary. Any local record of Keeper activity stores statuses, tiers,
  counts, one-way fingerprints, and SHA references. It does not store raw context
  bodies, source code, commands, or secrets.

## Distribution, stated honestly

The reusable part is the generic verifier core and the frozen result contract.
The valuable checks are gastown-specific: Beads schemas, `gt` conventions, and
mail formats. So "any MCP client can use it" is empty until a second adapter
exists. The first release proves the adapter pattern with the gastown adapter. A
signed, revocable distribution channel is a later phase, not part of this.

## Adoption

A tool users must find and wire up by hand gets close to zero organic adoption.
So the plan is not "publish a recipe and hope." It is an evidence-first ladder,
cheapest and most credible rung first. "Not a role PR" does not mean no upstream
presence. gastown's own guide invites configuration-level contributions and
states that integration is configuration, not compilation.

1. Dogfood and generate evidence. Wire the Keeper into your own fleet, run the
   seeded fault injection below, and produce a real number: how much drift it
   catches that the one-line "re-derive first" instruction misses, at what cost,
   with what false-positive rate. Nothing downstream moves without this. The
   proof is the adoption strategy, not a separate step.

2. Ship self-serve for early adopters. An MCP server plus a one-command hook
   recipe, listed where gastown users already look (an MCP registry or plugin
   marketplace). On its own this is weak distribution, and the plan does not lean
   on it.

3. Land a small upstream contribution, backed by the evidence. This is the real
   adoption engine, and it is a different PR from adding a role. Two forms, both
   worth doing:
   - An optional preset or hook-template line in gastown, so a user enables the
     Keeper with a config entry instead of hand-wiring it. This is the Tier 1
     preset and Tier 2 hook path gastown already documents for outside tools.
   - An optional check the Witness calls before it writes a "Verified" line. This
     is the wedge. The Witness writing verification by hand is a real reliability
     weakness in gastown, so a maintainer has reason to accept a change that fixes
     their own weakness, especially with fault-injection numbers attached.

The honest through-line: adoption does not come from the recipe. It comes from
proving the Keeper catches drift gastown's current path misses, then contributing
it back as optional config and an optional Witness check that maintainers want
because it makes their own system more reliable. The recipe is the on-ramp while
the evidence is built.

Caution: even this depends on you championing it and on maintainers being
receptive. If the evidence is weak, no rung moves, recipe or PR. The proof gates
everything, and the upstream contribution is a per-item sign-off decision, your
call.

## Proof: seeded fault injection

Matched live cohorts do not work inside gastown. Its work is real, one-shot, and
high-variance, and "a defect caused by bad inherited context" is an attribution
no one can make reliably. So the proof is deterministic fault injection.

1. Construct handoffs with known-stale structured claims: an issue marked closed
   in the handoff but reopened in Beads, a branch that was force-pushed, a merge
   that did not land, a file that moved.
2. Measure the Keeper's detection precision and recall on those planted claims.
   This is deterministic and needs no human judgment.
3. Run a session on each seeded handoff and measure whether the agent avoided the
   planted bad action when the Keeper flagged it contradicted.
4. Compare against the cheap baseline: the same sessions with only the one-line
   "re-derive before trusting a handoff" instruction and no Keeper.

The Keeper earns its place only if it catches drift the instruction misses, or at
lower total cost, without raising false contradictions on good claims.

## Open questions to resolve during planning

- SDK path. The Python MCP SDK v2 is at beta (2.0.0b1). Pin the beta hard, wait
  for stable, or build the server in TypeScript bridging to a Python core.
- Exact wire encoding of the frozen result across the CLI and the MCP tool.
  Freeze it and guard it with a test.
- Confirm the two call sites with a small spike: the hook recipe next to
  `gt prime`, and the Witness calling the MCP tool before writing "Verified."
- Enumerate the structured claim types, the store each maps to, its tier, and the
  independent Tier 0 source that can corroborate it.

## Risks and flags

- The core risk is that the Keeper's output is advisory. It appends a receipt it
  does not control, beside raw recollection it cannot remove, for an agent free
  to ignore it, in a system whose Witness and merge queue already catch the
  consequential errors. The mitigations are the Witness as first consumer (where
  the check replaces the assertion at its source), the behavioral contract, and a
  proof built to show the status actually changes the next action. If the proof
  cannot show that, the effort should stop.
- Upstream contribution. Any change to gastown is external. Your rule, tracked as
  continuo issue #1, is share-alike with per-item sign-off, nothing upstream
  without your yes. We design and prototype freely. A gastown PR is flag-and-stop.
- teamctx is still private, pending your flip. Publishing an MCP artifact waits
  for your go.
- Python MCP SDK is beta.

## Deferred (explicitly not v1)

Freeform claim extraction, Seance verification, replacing inherited text,
signal-triggered revalidation and any daemon, MCP resources and cache-hint
pitches, TUF signing and revocation, a persistent receipt ledger, matched-cohort
experiments, and any upstream "role" contribution.

## Success criteria

- For each supported structured field, the Keeper returns verified, contradicted,
  or unconfirmed, checked against git or Beads, with source, tier, and pinned
  provenance (git SHA and Dolt commit).
- A claim confirmed only by a Tier 1 record the claim's own author wrote returns
  unconfirmed, not verified.
- Keeper failure returns verification_unavailable, distinct from unconfirmed, and
  the agent keeps working.
- On seeded stale handoffs, the Keeper's detection precision and recall are
  measured, and flagged sessions avoid the planted bad action more often than the
  one-line-instruction baseline, without false contradictions on good claims.

## Provenance of harvested decisions

- ambara (ostinato-forge, private): one pure decision core shared by two callers
  (ADR 0003), schema freeze with a guard test (ADR 0001), credentials by
  reference (ADR 0002), pinned provenance, honest receipt.
- agent-efficiency (eparenti, private): the total-cost-to-verified-outcome
  objective, source trust tiers with corroboration and evidence requirements
  (forge-feeder ADR-002), fail-open and off-path runtime guards, the data
  boundary. The measurement approach was changed from that project's matched
  cohorts to fault injection, because gastown's live work is not cohort-matchable.
