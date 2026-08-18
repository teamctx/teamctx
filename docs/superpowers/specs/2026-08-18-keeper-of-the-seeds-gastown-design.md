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
4. The Keeper returns, per claim, a verified fact or an explicit "unknown," with
   the source it checked.
5. The hook injects the verified result into the agent's context in place of the
   unchecked recollection.

MCP surface (spec 2026-07-28):

- Resources first. teamctx facts map onto MCP resources, which are URI-addressed
  read-only data. Keep tools to a small set (one or two) for parameterized
  lookups a fixed URI cannot express. This respects client tool caps.
- Stateless. The current spec dropped session state, which costs teamctx nothing
  because it holds none.
- Cache hints. Because teamctx outputs are deterministic, it can honestly set
  strong `ttlMs` and `cacheScope` values on results. An LLM-based context server
  cannot. This is a concrete, demonstrable edge.

The honest-unknown contract must survive the protocol boundary. The Keeper
returns a structured result with an explicit status (verified, unknown, and the
source checked). It does not collapse "unknown" into an error or an empty
result, because that would destroy the one property teamctx exists to provide.

## How this meets both goals

- Distribution: the MCP server is a standalone, publishable artifact. gastown is
  the first consumer. Any other MCP client can use the same server.
- Proof: inside gastown, run agents on real work with the Keeper on and off, and
  measure whether verified inherited context reduces bad actions (for example,
  edits based on stale state, or acting on a closed issue as if open).

## Open questions to resolve during planning

These are deferred. They do not change the scope above.

- SDK path. The Python MCP SDK v2 is at beta (2.0.0b1). Options: pin the Python
  beta hard, wait for Python stable, or build the server in TypeScript (further
  along) bridging to the Python core. Shipping a public artifact on a beta SDK
  is a risk to weigh.
- Exact wire encoding of the "unknown" status within MCP resources and tool
  results.
- Exact gastown integration point. The provider integration guide documents a
  Tier 2 context-injection hook. The plugin system is a design proposal and not
  yet implemented, so the hook path looks like the real surface. Confirm with a
  small spike before committing.
- What counts as a verifiable claim. Define the claim types the Keeper accepts
  and the store each maps to (git, Dolt and Beads, events).

## Risks and flags

- Upstream contribution. A PR to gastown is an external contribution. Your own
  rule, tracked as continuo issue #1, is share-alike with per-item sign-off, and
  nothing goes upstream without your yes. We design and prototype freely. The
  actual contribution to gastown is a flag-and-stop, your call.
- teamctx is still private, pending your flip. An MCP server is a public
  artifact. Publishing waits for your go.
- Python SDK is beta, as noted above.

## Success criteria

- The Keeper returns a verified fact or an explicit "unknown" for each supported
  claim type, checked against a real gastown store, with the source named.
- The honest-unknown status survives the MCP round trip and is usable by a
  client.
- A measured before-and-after inside gastown shows fewer bad actions from
  inherited context when the Keeper is on.
