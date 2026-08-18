# Keeper of the Seeds: contributing teamctx to gastown

Date: 2026-08-18
Status: Design, pending review. No build approved yet.

## Summary

Contribute teamctx to gastown as a new role, the Keeper of the Seeds. The Keeper
is a deterministic, read-only ground-truth layer. When a gastown agent inherits
context from a dead predecessor, or is about to trust a claim that says
"Verified," the Keeper checks that claim against gastown's own reliable stores
and returns either a verified fact or an explicit "unknown." It never passes
forward a belief it cannot confirm.

This serves both goals we set:

- Distribution: teamctx ships as an MCP (Model Context Protocol) server, so the
  same artifact works in any MCP client, not just gastown.
- Proof: gastown is a live multi-agent coding system where bad inherited context
  causes real bad actions, so it is a place to measure whether honest context
  reduces agent mistakes.

## Objective

The Keeper optimizes one thing: the total cost to reach a verified, accepted
outcome, without reducing the requested scope, security, evidence, or quality
bar. Total cost includes model cost, failed attempts, rework, human review time,
and the cost of defects that escape.

The Keeper reduces that cost by removing bad inherited context, which causes
rework and defects. It must never reduce cost by injecting less-verified
context. It does not manufacture a "tokens saved" number. It reports measured
signals honestly. This objective is inherited from the agent-efficiency
capability layer, which set the same bar for guidance to coding agents.

## Background

teamctx is a deterministic, no-LLM, read-only context broker. It surfaces
verified facts and returns "unknown" instead of guessing. Its north star is
reality-grounding.

gastown is a multi-agent orchestration system in Go. It coordinates coding
agents (Claude Code, Copilot, Codex, Gemini, and others) across projects. Work
is stored as structured data (Beads in Dolt, a version-controlled database).
Every action is attributed to an actor. Agents are Polecats: persistent
identity, ephemeral sessions.

## The gap

gastown does several things well, and the Keeper stays out of them:

- Work as structured data (Beads, Molecules, Convoys, Hooks).
- Attribution and provenance (actor on every action, CV chains, event logs).
- Typed mail routing (POLECAT_DONE, MERGE_READY, and so on), which is
  machine-generated and git-backed, so already reliable.

Two spots are thin, and both are where teamctx is strongest:

1. Inherited context across dead sessions. Seance lets a new session query its
   predecessors for "context and decisions from earlier work." Handoff transfers
   work state into a fresh session. That inherited context is free-text
   recollection from an agent that no longer exists. Nothing verifies it. A new
   agent can act on what a dead predecessor believed, which may be stale or
   wrong.

2. Claims that assert verification without re-checking it. The mail protocol
   carries free-text lines such as `Verified: clean git state, issue closed`.
   That is an assertion made once by the sender, not an independent check at the
   moment another agent relies on it. The claim and reality can drift.

gastown names this gap itself. Its core principle NDI (Nondeterministic
Idempotence) is defined as getting useful outcomes from "orchestration of
potentially unreliable processes." It accepts that individual steps are
unreliable and compensates with persistence and oversight agents. It has no
component whose single job is a trustworthy, deterministic read of what is true
right now.

gastown even states the principle the Keeper would enforce. Its plugin design
opens with "Discover, Don't Track: Reality is truth. State is derived." The
Keeper is the piece that makes that true at read time.

## The role

The Keeper of the Seeds is gastown's ground-truth read layer.

The metaphor lines up with the mechanism. The seeds are the verified facts, the
real stock in a world where most context is toxic. The Keeper's defining act is
passing the seed bag forward before she dies, so the real stock survives across
the death of a session. That maps onto Polecats: persistent identity, ephemeral
sessions, with Seance and Handoff as the handoff. The Keeper carries verified
context across that death intact, and refuses to plant seed she cannot vouch
for.

## Scope

In scope:

- Verify inherited context at read time. When a session pulls context through
  Seance or Handoff, the Keeper checks each factual claim against gastown's
  reliable stores and returns a verified fact or an explicit "unknown."
- Re-verify "Verified" claims. When a claim such as `Verified: clean git state,
  issue closed` is about to be trusted, the Keeper re-checks it against current
  reality and reports the result.
- Return an honest "unknown" as a first-class answer, so an agent can act on "I
  do not know" rather than inherit a guess.

Out of scope (gastown already does these well):

- Work decomposition (Beads, Molecules, Convoys).
- Work routing and dispatch (sling, convoy).
- Agent lifecycle and recovery (Witness, Deacon, Refinery).
- Typed mail routing.
- Storage of state (Dolt).
- Attribution and provenance of actions.

The Keeper reads gastown's stores. It does not write to them and does not enter
any trusted path on its own. Its output is advisory context handed to an agent.

## Verification model

This is the core of the Keeper. It decides what counts as a verified fact and
what stays unknown.

### Source trust tiers

Every source the Keeper reads carries a trust tier. This model is adapted from
the agent-efficiency source trust tiers.

- Tier 0: hard, machine-checkable ground truth. Git state (commits, branches,
  merge status), Dolt and Beads records (issue status, bead state), and event
  logs.
- Tier 1: attributed, structured, machine-generated records that are reliable
  but one step removed, such as typed mail bodies.
- Tier 2 and lower: free-text recollection from an agent, including a
  predecessor's Seance context and a hand-written "Verified" line.

A claim from a Tier 2 or lower source is a candidate, never a verified fact on
its own. It becomes a verified fact only when it is corroborated against a Tier
0 source. If it cannot be corroborated, the Keeper returns "unknown." A
predecessor saying "the issue is closed" is a candidate; the Keeper confirms it
against Beads before an agent may treat it as fact.

### One pure decision core

Both entry points (verify inherited Seance or Handoff context, and re-check a
"Verified" claim) run through one pure, deterministic decision function. Same
inputs give the same result, and the function performs no I/O. This follows
ambara's `plan_remember` pattern, where a single frozen decision contract served
two callers so the security-sensitive path could not drift between them. The
Keeper's callers cannot diverge on what counts as verified.

The decision function takes a normalized claim plus the tier-labeled evidence
read from the stores, and returns a result: a status (verified or unknown), the
final trust tier, the source checked, and a receipt.

### Frozen contract and guard test

The result shape (status, tier, source, provenance, receipt) is frozen as v1 and
pinned by a guard test that fails on any drift. Changing it requires a new
decision record that supersedes the old one, landed in the same change as the
test update. This follows ambara's schema-freeze discipline and protects the one
property teamctx exists to provide, so "unknown" cannot silently degrade into an
error or an empty result.

### Provenance, receipt, and expiry

- Provenance: every verified fact carries a stable, versioned provenance record
  naming the store and the record checked, and when. This follows ambara's
  frozen provenance footer.
- Receipt: every answer carries a compact receipt of what was checked, against
  which store, at which tier, and what could not be confirmed. The Keeper does
  not overclaim. This combines ambara's honest receipt with agent-efficiency's
  selection receipt.
- Expiry: a verified fact is not verified forever. It carries a freshness bound.
  Past that bound the Keeper revalidates rather than trusting recency. This
  follows agent-efficiency's rule that "latest" means reviewed, applicable, and
  unexpired, and recency alone is not a quality signal.

## Architecture

teamctx stays in Python. gastown is in Go. They do not share code. teamctx runs
as its own process and speaks MCP. This matches gastown's stated integration
model: loose coupling through configuration and hooks, no compilation, no
importing of agent code.

Data flow:

1. A gastown agent starts a session or requests predecessor context.
2. gastown's context-injection hook (Tier 2 in gastown's provider integration
   guide) calls the Keeper over MCP with the claims to verify.
3. The Keeper reads gastown's reliable stores read-only: git state, Dolt and
   Beads, and event logs.
4. The Keeper runs the pure decision core and returns, per claim, a verified
   fact or an explicit "unknown," with the source, tier, provenance, and
   receipt.
5. The hook injects the verified result into the agent's context in place of the
   unchecked recollection.

MCP surface (spec 2026-07-28):

- Resources first. teamctx facts map onto MCP resources, which are URI-addressed
  read-only data. Keep tools to a small set (one or two) for parameterized
  lookups a fixed URI cannot express. This respects client tool caps.
- Stateless. The current spec dropped session state, which costs teamctx nothing
  because it holds none.
- Cache hints. Because teamctx outputs are deterministic, it can honestly set
  `ttlMs` and `cacheScope` values on results, bounded by the fact's expiry. An
  LLM-based context server cannot. This is a concrete, demonstrable edge.

The honest-unknown contract must survive the protocol boundary. The Keeper
returns the frozen structured result described above. It does not collapse
"unknown" into an error or an empty result.

## Efficiency and viability

The Keeper runs on every Seance and Handoff across a fleet of Polecats. It must
be practical at that scale, and these rules come from the agent-efficiency
runtime, which had the same constraint.

- Fail open. If the Keeper is down or errors, gastown agents keep working, with
  the affected context marked unknown. The Keeper never blocks an agent. This
  matches teamctx's assurance-state model: advisory, never in the trusted path.
- Off the hot path. Verification is deterministic, local, and cheap. No network
  call and no model call sit in the hook hot path. The Keeper is not a latency
  multiplier across many agents.
- Sparse and quiet. Injected context is capped, deduplicated, and silent when
  nothing needs verifying. Less inherited text also means a smaller surface to
  poison.
- Signal-triggered, ranked revalidation. The Keeper does not re-verify all
  inherited context on every read. It verifies the claims a real gastown signal
  (a merge, a status change, a moved file) suggests may have drifted, ranked by
  relevance to the current work. This follows ambara's curation engine, which
  emitted confidence-scored revalidation advisories from real signals.
- Compact payload with deferred bodies. The Keeper injects a lean result (the
  fact, its status, tier, provenance, and a short receipt) and defers full
  source records to explicit reads through MCP resources. A coverage guardrail
  test ensures shrinking the payload never drops a verified fact the agent needs.
  This follows ambara's manifest-plus-deferred-bodies design and its
  token-cost guardrail tests.

## Security and data boundary

- Credentials by reference only. If a gastown store needs auth, credentials are
  named by reference and resolved at runtime by trusted code. Raw credentials
  never enter verified facts, receipts, caches, or injected context. This
  follows ambara's auth-broker contract.
- Receipt ledger boundary. Any local ledger of Keeper activity stores
  dispositions, counters, tiers, one-way fingerprints, and SHA-256 references.
  It does not store raw context bodies, source code, commands, or secrets. This
  follows agent-efficiency's data boundary.
- Signed distribution (later). For the distribution goal, if teamctx ships
  broadly as an MCP artifact, sign it and support monotonic revocation of a bad
  version, following agent-efficiency's TUF-based signing and revocation. This is
  a later phase, not part of the first gastown integration.

## How this meets both goals

- Distribution: the MCP server is a standalone, publishable artifact. gastown is
  the first consumer. Any other MCP client can use the same server.
- Proof: inside gastown, run agents on real work with the Keeper on and off, and
  measure whether verified inherited context reduces the total cost to a
  verified accepted outcome. The protocol is below.

## Measurement protocol for the proof

The proof uses a matched experiment, adapted from the agent-efficiency
measurement protocol. Vague "it seems better" claims do not count.

- Cohorts. Enroll each fresh session in a named cohort, Keeper on or Keeper off,
  immediately at session start, before the task is given.
- Preregistered tasks. Both cohorts draw from the same preregistered task set,
  bound by a SHA-256 digest. Keep host, model, effort, repository, and task
  class stable across cohorts.
- Primary metric. Compare the total cost to reach a verified accepted outcome,
  not the cost of the first answer. Capture model cost and tokens when the host
  reports them, wall-clock time to acceptance, failed tool calls and
  repeated-action signals, user correction turns, escaped defects and review
  findings, and human review minutes.
- Immutable ledger. Enrollment, outcomes, and utility ratings cannot be
  rewritten. Corrections are appended as exclusions with a reason
  (data-entry-error, protocol-deviation, or evidence-withdrawn). Turning the
  Keeper off is always allowed and is recorded as an exclusion.
- Evidence by reference. Every non-empty acceptance outcome carries a named
  evidence kind and a SHA-256 reference to the external artifact. The ledger
  does not store the artifact bytes.
- Utility judgment. For each injected verified fact, rate it useful, neutral, or
  distracting, and whether it changed the agent's next action. Prefer blinded
  judgments, made without revealing the expected result first.
- Read the outcome. Compare medians and inspect outliers. Do not rely on one
  aggregate score.

The Keeper earns its place only if it lowers the cost to a verified accepted
outcome without lowering acceptance quality.

## Open questions to resolve during planning

These are deferred. They do not change the scope above.

- SDK path. The Python MCP SDK v2 is at beta (2.0.0b1). Options: pin the Python
  beta hard, wait for Python stable, or build the server in TypeScript (further
  along) bridging to the Python core. Shipping a public artifact on a beta SDK
  is a risk to weigh.
- Exact wire encoding of the frozen result (status, tier, source, provenance,
  receipt) within MCP resources and tool results. Whatever we pick, freeze it
  and guard it with a test.
- Exact gastown integration point. The provider integration guide documents a
  Tier 2 context-injection hook. The plugin system is a design proposal and not
  yet implemented, so the hook path looks like the real surface. Confirm with a
  small spike before committing.
- Claim types and store mapping. Define the claim types the Keeper accepts, the
  store each maps to, and the trust tier of each store.

## Risks and flags

- Upstream contribution. A PR to gastown is an external contribution. Your own
  rule, tracked as continuo issue #1, is share-alike with per-item sign-off, and
  nothing goes upstream without your yes. We design and prototype freely. The
  actual contribution to gastown is a flag-and-stop, your call.
- teamctx is still private, pending your flip. An MCP server is a public
  artifact. Publishing waits for your go.
- Python SDK is beta, as noted above.

## Success criteria

- For each supported claim type, the Keeper returns a verified fact or an
  explicit "unknown," checked against a real gastown store, with the source,
  tier, and provenance named.
- A claim from a low-tier source is treated as a candidate and is not reported as
  verified without Tier 0 corroboration.
- The frozen result, including the "unknown" status, survives the MCP round trip
  and is usable by a client.
- The Keeper fails open. When it is down or errors, agents keep working with the
  affected context marked unknown.
- A matched cohort experiment inside gastown shows lower total cost to a verified
  accepted outcome with the Keeper on, without lower acceptance quality.

## Provenance of harvested decisions

For traceability, the ideas adapted from prior work:

- ambara (ostinato-forge, private): one pure decision core shared by two callers
  (ADR 0003 remember-core-and-promote), schema freeze with a guard test (ADR
  0001), credentials by reference (ADR 0002 auth-broker), frozen provenance
  footer, honest receipt, signal-triggered ranked revalidation and
  compact-plus-deferred payload with token-cost guardrails (curation core and
  context token-efficiency tests).
- agent-efficiency (eparenti, private): the total-cost-to-verified-outcome
  objective, source trust tiers with corroboration and evidence requirements
  (forge-feeder ADR-002), fail-open and off-hot-path and sparse-quiet runtime
  guards, the matched-cohort measurement protocol with an immutable ledger and
  evidence by reference, utility judgments, expiry and "recency is not quality,"
  the data boundary, and TUF signing with revocation for distribution.
