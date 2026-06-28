# Competitive landscape: the "context engine for engineering" category (2026-06)

**Date:** 2026-06-27 · **Status:** verified on the load-bearing claims (see Verification)

## The question this answers

Not "is teamctx's internal construction novel" but: **does a product that does teamctx's job
already exist for sale?** A buyer-facing question, not an architecture one.

## Short answer

**The job exists and is an occupied, funded category. The specific product, with teamctx's
properties, does not.** teamctx is a *contrarian-mechanism bet inside an occupied category*,
not a greenfield. That is a stronger position than "no competitors" (the category proves
demand) and a different risk profile (the risk is differentiation/co-option, not "nobody wants
this").

## The category and the neighbor

There is a named, funded category: the **"context engine for engineering."**

- **Direct neighbor, [Unblocked](https://getunblocked.com/):** indexes code, PRs, tickets,
  docs, and conversations; permission-aware; delivers context to coding agents (Claude Code,
  Cursor, Copilot, Windsurf) **over MCP**. Same sources, same surface, same buyer, same stated
  problem as teamctx ("engineering knowledge is fragmented across the PR, the ticket, the Slack
  thread, and the code").
- **Above it, [Glean](https://www.glean.com/):** enterprise search, broader scope.
- **Code-context slice, [Augment Code](https://www.augmentcode.com/context-engine)
  ("Context Engine"), Sourcegraph:** semantic search over the codebase.

Our existing landscape doc benchmarks teamctx against **agent-memory** (Mem0, Letta). That is
the wrong foil, easy to win and not where the real competition is. The realer competitor is
this context-engine category. (See [agent-memory landscape](landscape-agent-memory-2026-06.md)
for the foil we *over*-weighted.)

## Same job, opposite mechanism (the whole bet)

Unblocked is, on every axis that defines teamctx, the mirror image, **by design**:

| teamctx | Unblocked (closest competitor) |
|---|---|
| Deterministic, no LLM in the trusted core | LLM synthesis (RAG), "delivers a single reconciled answer" |
| Surface the conflict, refuse to adjudicate | "resolves what conflicts… recency and authority signals resolve contradictions automatically" |
| Proactive push at work-start, unprompted | Pull / Q&A, agent asks, it answers |
| **Absence ≠ safety**: reports what it could not see (honest-UNKNOWN) | No coverage-honesty notion at all |
| Existence-privacy as a formal property | "Access control from source systems" (show-only-what-you-can-read, not non-leakage of existence) |

**Sharpest discriminator:** Unblocked uses the *same signals* teamctx uses, freshness,
authority, source type, but to **collapse a conflict into one answer**, where teamctx uses them
to **flag staleness and refuse to pick**. Same inputs, opposite output philosophy. That is not a
flag an incumbent can bolt on; it's the difference between a product that wants to **answer** and
one that wants to **assure**. That distinction is the whole teamctx bet, and it is unoccupied.

## What no one appears to sell

After scanning context engines, collision/merge tooling, deterministic MCP analyzers, and
agent-assurance/provenance:

- **Deterministic / no-LLM-in-core context for agents.** Everyone in the category is RAG + LLM.
  The one "deterministic" hit,
  [Context Engine (contextenginehq)](https://github.com/contextenginehq/context-engine), does
  deterministic context *compression* to a token budget, a different job (the headroom-style
  foil; see [[reference_headroom]]). The one no-LLM-over-MCP tool,
  [Repowise](https://github.com/repowise-dev/repowise), does deterministic code-health scoring,
  not cross-source work-state.
- **"Absence is not safety" as a product property.** No product emits "I couldn't see this
  source" as a first-class output. Unoccupied.
- **Surface-don't-adjudicate as a stance.** The incumbent does the opposite by design.
- The **collision slice** alone is a mature category (Reviewpad, Aviator, Mergify, Graphite),
  but for human/CI merge-conflict prevention, not as agent work-start context.

*Honesty caveat on the negative:* a negative can't be proven exhaustively; this is past the
training cutoff and US-only search. No exact match was found where one would expect it, and the
nearest neighbor is mechanistically opposite, strong evidence, not proof.

## Strategic read

Not greenfield, a contrarian-mechanism bet inside an occupied category. Two real risks:

1. **Good-enough.** Unblocked's probabilistic answer covers the whole messy surface, including
   the unstructured slice teamctx's own E2 number says structural relevance can't certify. We
   are deliberately *narrower-but-trustworthy* against *broader-but-confident*. A buyer who
   doesn't feel the absence-equals-safety pain acutely may not care.
2. **Co-option.** The *thin* differentiators (proactive push, source-permission inheritance) an
   incumbent can bolt on. The *deep* three, **determinism/no-LLM, coverage-honesty,
   surface-don't-adjudicate**, require *not being an LLM-synthesis product*, which a RAG
   incumbent cannot easily become. **Lead with the deep three; never the thin two.**

**Positioning consequence:** lead not against agent-memory (a strawman) but against
Unblocked/Glean, *"they synthesize one confident answer and resolve your conflicts for you; we
hand the agent the evidence, flag the conflict, and tell it what we couldn't see, because for
the trust-critical slice you want assurance, not a good guess."*

## Verification

Independently confirmed today (2026-06-27) against Unblocked's own site: it is "the context
engine for modern engineering teams," serves coding agents over MCP, and **"synthesizes across
all your sources, resolves what conflicts, and delivers a single reconciled answer,"** with
**"Conflict resolution, recency and authority signals resolve contradictions automatically,"**
and **no coverage-honesty / unknown-reporting notion**. Their exact internals (LLM vs. hybrid)
aren't fully published, but the *output philosophy* (resolve-one-answer) and the *absence of
honest-UNKNOWN*, the two claims the positioning rests on, are confirmed from their own copy.
The broader category scan is carried over from prior research and not re-verified item-by-item.

## Sources

- [Unblocked, the context engine for engineering](https://getunblocked.com/)
- [Unblocked MCP, context for AI coding agents](https://getunblocked.com/unblocked-mcp/)
- [Unblocked vs Glean](https://getunblocked.com/blog/unblocked-vs-glean/)
- [Augment Code, Context Engine](https://www.augmentcode.com/context-engine)
- [Context Engine (contextenginehq), deterministic token-budget selection](https://github.com/contextenginehq/context-engine)
- [Repowise, deterministic no-LLM repo analysis over MCP](https://github.com/repowise-dev/repowise)
