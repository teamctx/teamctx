# teamctx: Positioning (resolves open-item #10)

*Decided 2026-06-19, resolving §4 open-item #10. **Supersedes** the prior positioning
order in [architecture-decision.md §0](architecture-decision.md) (the "lead with
can't-track" lock). Driven by the [role-play panel](../../research/reviews/roleplay-panel-2026-06-18/convergence.md)
(5/5 independent: trust opens the **buyer** gate; rework drives **adoption**) and the
category-up reframe in design dialogue. Bar: **claims never outrun proof**: the
credibility engine below is a **proof obligation, not a slogan**.*

---

## The stack (top = narrative frame; down to the proof under it)

**Why now, the vision frame.** Agents broke the speed at which work moves; human team
coordination hasn't caught up. teamctx is the connective tissue that lets a team *and its
agents* operate at agent speed without the wheels coming off. *Aspirational by nature*:
it sits **on top of** the concrete proof and is **proven backwards from real usage**, not
asserted up front.

**Marquee, the category.** ***Timely, ambient team context***, humans and their agents
working from the same live picture of the current state of the work and the standards
around it. The load-bearing word is **context, not memory**: the stateless broker delivers
*currently-true, non-retained* context (the data already lives in the source systems;
teamctx transforms the **delivery**, not the content). "Memory", durable, accumulated, is
the **optional second package**, never the marquee.

**Lead benefit + supporting set.** Capability-forward, never deficit-framed. *(Reject
"never work blind": a disability metaphor that leads with an absence.)* Lead with the
most-felt, **fewer collisions, less rework**: with the rest in support: standards
actually adhered to · faster ramp & resumption · cross-agent continuity · fewer
stale-spec / missed-gate mistakes. A **lead with a supporting set**: hierarchy, not one
feature, not a flat list of six co-equals.
*Honesty hedge (on-brand):* it **informs; it does not enforce.** The benefit is an
**input** (better-informed work), more-likely-than-not *when the team acts on it*: never
a guaranteed outcome.

**The "because", the credibility engine (THE thing to nail).** No LLM *in the content
path* → facts arrive **verbatim, source-backed, verifiable** → teamctx is the
**deterministic ground an agent can stand on and check itself against.** Complementary to
the LLM, *never* adversarial, the product exists **because** of agents: the LLM does
judgment and generation, teamctx hands it trustworthy current facts. Scoped precisely: the
reference for *"what is currently true in the record,"* **not** *"what's the right call"*
(the agent's job) or *"is the record correct"* (fidelity ≠ truth). The same construction
means it **can't track** (non-retention) and **can't be hijacked** (feature-mediated
selection).

> **Proof obligation (Edgar, 2026-06-19).** "Credibility engine" is a *claim*, and if we
> nail it we have a much better chance of winning, so it must be **backed, not
> asserted**. The evidence is: determinism · verbatim source-backing · **one-click
> verifiability** (digest + diff link on every card) · **replayable certificates**. This
> is the **highest-leverage thing to get right** in the build.

**Table stakes (stated as "of course," never the headline).** It **cannot cause harm**: a
required feature even for a solo dev, delivered for free by the same construction.
Safety-*of-teamctx* is table stakes; the *construction that produces it* is the credibility
engine above, do not confuse the two.

**Scope.** Primary consumer = a **human using an agent**, who acts on the context.
Autonomous agents = adjacent, harder sell, later. Iterate scope from real usage.

---

## What changed from the prior lock, and why

- **Prior (architecture-decision §0):** marquee = *can't-track by construction*; co-lead =
  *can't-be-hijacked*; payoff = honest-coverage + velocity; token/latency = objection-
  handler. Ranked by **fear-severity × irreversibility**.
- **The finding:** that ranking is a **buyer's** lens (security/CTO rank by fear). The
  role-play panel (5/5, independent) showed it's wrong for **adoption**: trust/can't-track
  gets you *past the gate*; the felt **rework/collision** win is what gets devs to use it
  and VP-Eng to mandate it. For an OSS, adoption-judged product whose own day-in-the-life
  *leads with a solo founder*, the motion is bottoms-up.
- **The resolution:** lead with the **category** (it serves both audiences at once);
  **demote** can't-track/determinism from *marquee* to the *credibility engine*: it does
  not disappear, it becomes the **because** that makes the category claim trustworthy and
  the differentiator vs. probabilistic AI; **demote** safety to table stakes. **Not a "dual
  banner"** (two banners = none), one marquee, one lead benefit, one credibility engine.

---

## Differentiation vs. context-engines: the PRIMARY competitor (added 2026-06-27)

*Driven by [competitive analysis](../../research/competitive-context-engines-2026-06.md): the real
neighbor is the "context engine for engineering" category, **Unblocked** (above it, Glean), NOT
the agent-memory wave. Same sources, same MCP surface, same buyer, **opposite mechanism.** Full
strategy: [reality-grounding](reality-grounding-strategy-2026-06.md).*

Unblocked synthesizes your PRs, tickets, docs, and chat into **one reconciled answer** and resolves
contradictions for you (recency/authority). teamctx is the mechanistic mirror image, by design:

- **They transform; we attest.** They put an LLM in the content path and return the model's
  interpretation; we keep no LLM in the content path and return the record verbatim, source-backed
  (delivery transformed, *content* not).
- **They resolve; we surface.** They collapse a conflict into one answer; we flag it and let the
  human/agent judge.
- **They answer; we admit gaps.** They have no coverage-honesty; our UNKNOWN says where *not* to
  trust the green.
- **Same signals, opposite output:** both use freshness/authority, they to pick a winner, we to
  flag staleness and refuse to pick.

**Lead against this category, not agent-memory.** The deep three, no-LLM-in-content-path,
coverage-honesty, surface-don't-adjudicate, a RAG synthesizer structurally cannot retrofit; the
thin diffs (proactive push, source-permission) it can. Lead with the deep three. Core value,
plainly: *a confident wrong answer delivered through a terminal you trust is worse than no answer
at all.*

## Differentiation vs. agent-memory ecosystem: the *secondary* foil (added 2026-06-25)

*Note (2026-06-27): this is the **lesser** foil, easy to differentiate from and not where the real
competition is; the primary competitor is the context-engine category above. Original driver below.*

*Driven by landscape analysis of RH ET "From context to dreams" blog (Jun 2026) and the
broader agent-memory wave (Mem0, OpenClaw memory, Anthropic Managed Agents memory,
Langgraph memory). See [landscape note](../../research/landscape-agent-memory-2026-06.md).*

The industry is converging on **agent memory**: LLM-augmented write-back storage that
solves "agents forget." teamctx solves **"agents can't safely coordinate"**: a different
problem in the same neighborhood. The distinction:

- **Memory = recall.** An agent remembers what it learned. Probabilistic, LLM-extracted,
  mutable, dreaming-consolidated. Solves single-agent continuity.
- **Context = assurance.** An agent knows what's currently true in the team's work. 
  Deterministic, source-backed, read-only, verifiable. Solves multi-agent coordination.

teamctx **complements** memory systems, it is the trust layer that governs what crosses
agent boundaries once agents have their own memory. The same "enterprise mind" vision that
the memory ecosystem aspires to requires a non-probabilistic coordination substrate
underneath it. That substrate is teamctx.

**The credibility engine is the differentiator:** when the industry converges on
probabilistic memory as the default, deterministic source-backed delivery becomes the
scarce thing. teamctx's construction, no LLM in the content path, verbatim, verifiable,
non-retained, is not a limitation, it's the **reason to exist alongside** the memory
layer.

---

## Still open (copy, not strategy)

- The exact **lead-benefit wording**, written against a real page. The same lead may render
  differently on a dev-facing README (the felt rework/collision win) than on a
  security-facing page (the can't-track/can't-be-hijacked credibility), but the **marquee
  is shared**, only the proof point nearest it is audience-targeted. A copy decision, not
  a positioning one.
