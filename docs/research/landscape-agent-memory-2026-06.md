# Landscape: Agent Memory (June 2026)

*Captured 2026-06-25 from Red Hat Emerging Technologies blog + next.redhat.com/projects.*

## Source

"From context to dreams: architecting memory for AI agents" (Rampal, Capper, Romashko,
Jackson, Cook — Jun 1, 2026). Part of an RH ET editorial push that includes a 3-part
zero-trust-for-agents series (Pavel Anni, Kevin Cogan, Morgan Foster) and a
securing-agent-communication post.

## Their framing

Agent capability = model + harness + **memory** + environment + evolution. Memory is an
LLM-augmentation layer: embedding-based vector storage, semantic/episodic types,
"dreaming" (background consolidation), hierarchical shared memory pools
(agent → team → enterprise → "enterprise mind"). Demo: OpenClaw + Mem0 plugin
remembering a weather-API project between sessions.

## Where teamctx differs (the positioning wedge)

| Dimension | Agent-memory ecosystem | teamctx |
|---|---|---|
| **Problem** | "Agents forget" | "Agents can't safely coordinate" |
| **Mechanism** | Write-back memory (LLM extracts, stores, recalls) | Read-only broker (delivers currently-true context from source systems) |
| **Trust model** | Implicit — anyone writes, semantic retrieval, no verification | Evidence/authority split, labeled verdicts, source-backed + verifiable |
| **Determinism** | Probabilistic (embedding similarity, LLM extraction, "dreaming") | Deterministic (no LLM in content path, verbatim delivery) |
| **Cross-agent** | Shared memory pools — collective knowledge base | Broker with existence-privacy projection — controlled visibility |
| **Data integrity** | "Agent memories remain distinct from source-of-truth databases" (policy) | Read-only by construction (structural, not policy) |

## The trust gap they don't address

The blog never asks:
- Who gets to write to shared memory?
- What happens when two agents write conflicting things?
- How do you verify what's in the shared pool?
- How do you audit what context an agent acted on?

Their "hierarchical memory" is about *access*. teamctx is about *assurance*. Once you have
multiple agents with shared memory, you need something that isn't memory to govern what
crosses boundaries — that's the broker.

## "Dreaming" as a liability

Their "dreaming" concept (background processes that "derive new knowledge" and "form new
memory associations") is the opposite of deterministic. For enterprise contexts where you
need to *know* what an agent knew and why it acted, dreaming is a liability, not a feature.
teamctx's construction makes this impossible by design — the same construction that
produces the credibility engine.

## Positioning implication

teamctx complements, not competes. Memory solves recall; teamctx solves coordination
trust. The article sets up the need for teamctx without realizing it: the "isolated agents"
problem (#4 in their challenge list) needs more than shared memory — it needs a trust layer
for what crosses agent boundaries, and that layer can't be probabilistic.

**Lead with:** "Memory is necessary but not sufficient. You also need a trust layer for
what crosses agent boundaries — and that layer must be deterministic."

## Internal allies (Red Hat ET)

- **RH Secure Sign team** (Sigstore distribution) — Siglum v2's integrate-don't-compete partners
- **"Context to dreams" authors** (Rampal, Capper, Romashko, Jackson, Cook) — closest
  thought-neighbors on agent context; their work frames the problem teamctx solves
- **Zero-trust-for-agents series** (Anni, Cogan, Foster) — agent identity/trust;
  teamctx's authority model + Siglum's attestation are answers to their questions
