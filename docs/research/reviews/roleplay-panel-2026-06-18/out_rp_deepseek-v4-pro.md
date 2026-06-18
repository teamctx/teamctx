ROLE 1 — CPO / Head of Product

**The ONE product bet most likely to be WRONG.**  
That a stateless, cross-system metadata broker without LLM mediation will be trusted as a source of truth by developers. Developers don’t read documentation; they trust what they last saw. Cards will be ignored unless the system makes ignoring them impossible. Without enforcement, the signal-to-noise ratio must be flawless or it’s garbage.

**Wedge: painkiller or vitamin?**  
Painkiller only for the rework cost. First adopter: the platform team at a 400‑dev enterprise that’s already burned by an agent merging with stale acceptance criteria and causing a rollback. They don’t buy because it’s safe—they buy because rework is a crisis. Solo builders adopt if the on‑boarding is zero-install and the delta‑against‑last‑session is trivially consumed.

**“Another tool to manage” — indispensable vs. shelfware.**  
(a) Solo: indispensable if it’s a single, no‑auth‑required command (`teamctx diff` from last session) that fits into their start‑of‑day script, else it’s dead. (b) Enterprise: indispensable only if it plugs into the agent’s tool‑use protocol and actively pauses misaligned work—otherwise it’s yet another dashboard that nobody looks at. Must become invisible infrastructure.

**CUT from v1.**  
The collective‑memory layer. That’s a governance graph that requires organizational maturity. v1 must be a pure, zero‑setup broker with a fixed set of connectors (GitHub, Jira, Confluence) and a read‑only API surface that agents can call directly. Ship the rework elimination; add team learning later.

**What would make ME champion it.**  
I see a pre‑post measurement showing >20% reduction in wasted agent tokens and human re‑review time on pull requests that conflict with parallel work. That number makes it a must‑have, not a nice‑to‑have.

---

ROLE 2 — Head of Engineering / Platform

**Would my teams run it? The operational objection that matters most.**  
We’d pilot it, but the daemon is a new SPOF for agent context freshness. If the daemon is slow or down, agents lose their context window, and engineers will rightfully blame us for broken CI runs. The operational burden is not the daemon itself—it’s maintaining connector auth, schema drift from Jira/Confluence, and verifying that absence is truly absence, not a broken integration. One silent connector failure and the cards become dangerously misleading.

**“My devs route around it / feel surveilled” risk.**  
Real, but managed because the product is artifact‑only and explicitly not surveilling people. However, if a developer gets a card like “acceptance criteria changed since your branch started” and it’s a false positive because the Jira issue was merely re‑indexed, they’ll route around it permanently. Trust is binary: either the cards are perfectly accurate or the tool is dead.

**Trust: the single failure that makes engineers stop reading.**  
A **phantom card**—a card claiming a doc was updated that wasn’t, due to a timestamp misinterpretation. The design’s determinism and explainability could save it if the card includes a cryptographic digest of the source change and a direct link to the diff. But if that evidence isn’t one‑click verifiable, engineers will dismiss all cards within a sprint. The design must not only be correct—it must prove correctness instantly.

**Honest reason a pilot stalls after week 2.**  
The cards are accurate but irrelevant. “Open PR touches same file” fires constantly in a monorepo, desensitizing everyone. Noise kills. The system needs policy gates to tune card surfacing per repo/team, and v1 ships without them. Engineers ignore the feed, and the pilot ends.

---

ROLE 3 — Exec sponsor (impact lens: adoption/trust/impact)

**Impact thesis in one line — clears the bar?**  
teamctx eliminates the invisible tax of re‑deriving cross‑system context during AI‑assisted development, converting wasted compute and re‑review time into a deterministically lower cost per change—if adopted, it’s a margin multiplier on every PR. Clears the bar to sponsor.

**Blind spot most likely to kill exec support.**  
The adoption vector is a pull model with no enforcement; it relies on agent builders and developers to voluntarily query the cards. Without a push into the coding workspace (IDE, agent runtime), the context won’t be consumed. The product is a library, not a product until it’s woven into the default toolchains. I’ll cancel sponsorship if the integration story remains “MCP/CLI/file/hooks” with no opinionated agent‑side adapters that interrupt work when a high‑priority card appears.

**Banner: safety boundary vs. everyday rework win.**  
Lead with the rework win. Safety is the table stakes that let it into the enterprise—it’s the “compliance says yes” slide for the CTO, but it does not drive developer pull. Engineers don’t wake up to fix prompt injection; they wake up to avoid redoing a feature because a teammate’s branch snuck in. Lead with “Stop rebuilding state from scratch. Stop rework.” The safety banner makes it sound like a firewall, which is someone else’s problem.

---

**Out of character, one paragraph:**  
The single biggest blind spot is the absence of an implicit notification model in the developer’s immediate working environment. The product envisions context cards being pulled by agents, but developers don’t live in their agents. Without a lightweight, IDE‑native notification (e.g., a status bar badge or a smart commit‑hook warning) that surfaces high‑priority cards at the point of action, the rework prevention promise evaporates because the signal never reaches the human who is about to open a merge request. The system must embed itself into the places where work is done—not just where agents query.