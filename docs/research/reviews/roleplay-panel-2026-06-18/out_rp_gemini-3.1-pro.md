**ROLE 1, CPO / Head of Product**

*   **The ONE wrong bet:** "No IDE plugins." You are forcing a workflow change. Devs live in the IDE; if the context broker requires them to switch to a CLI to read cards before hitting "generate" on their agent, they will just hit generate. MCP helps for agent-reading, but human-visibility needs to be exactly where the human is typing. 
*   **Wedge:** It’s a vitamin for the solo dev, but a bleeding-neck painkiller for the 400-dev enterprise. First adopters are Platform teams terrified of Promise 3 (Safety/Injection), but the *users* (devs) will only adopt for Promise 1 (Rework savings). 
*   **Indispensable vs. Shelfware:** 
    *   *(a) Solo dev:* Shelfware. The cognitive load of tracking their own state is low; they don't need a broker.
    *   *(b) 400-dev enterprise:* Indispensable *if* it reliably catches the "two devs asking agents to refactor the same shared library simultaneously" collision.
*   **Cut from v1:** The "optional collective-memory layer." Kill it. It introduces state, governance debates, and feature creep. Ship the stateless deterministic broker and prove the core routing works first.
*   **To champion it:** Make it completely invisible. I will champion this the day a developer doesn't even know `teamctx` exists, but their Claude agent magically stops hallucinating outdated API specs because the broker silently injected the updated Confluence truth-state via MCP.

**ROLE 2, Head of Engineering / Platform**

*   **Operational objection:** "Permission-faithful" is a nightmare to run. To accurately mirror Jira, GitHub, and Confluence RBAC/IAM in a warm daemon cache means we are constantly polling or building webhooks across fragile enterprise SaaS APIs. The moment our corporate Okta syncs lag, your daemon breaks.
*   **Surveillance risk:** Managed on paper ("artifact-only"), but real in practice. If managers realize they can query the daemon to see how often a dev triggers "acceptance criteria changed" cards, it becomes a shadow metric. We must hardcode the inability to aggregate logs by user.
*   **Trust failure:** A stale-shown-as-fresh card on a PR. If a dev pushes a commit, immediately triggers an agent, and the warm daemon (lagging by 45 seconds) tells the agent "no open PR touches this," the agent will clobber the dev's work. One clobbered file and the dev will bypass `teamctx` forever. 
*   **Pilot stall (Week 2):** Alert fatigue. If every prompt emits five cards saying "linked doc updated 4 months ago," devs will mentally classify `teamctx` outputs as spam. If it prints, it must be an immediate, blocking-level conflict.

**ROLE 3, Exec Sponsor**

*   **Impact thesis:** "Eliminates the AI-generated rework tax caused by agents acting on isolated, stale, or conflicting organizational state." Yes, it clears the bar, AI ROI is currently bleeding out through rework.
*   **Exec blind spot:** Assuming our systems of record are actually accurate. If Jira is a graveyard of outdated tickets and Confluence is full of deprecated architecture docs, `teamctx` will deterministically force our agents to follow garbage instructions. You are bridging agents to our organizational dysfunction.
*   **The Banner:** "Safety boundary" gets you past the CISO to install the pilot. "Everyday rework" gets the VP of Engineering to mandate it across the floor. Lead with rework for the business; keep safety in your back pocket as the compliance trump card that prevents InfoSec from vetoing us.

***

**OUT OF CHARACTER**

The single most important thing this vision is not seeing is the **"Garbage-In, Garbage-Out" (GIGO) paradox of enterprise systems of record**. A deterministic, non-LLM broker assumes that the source text in Jira or Confluence is a reliable ground truth that should alter agent behavior. In reality, enterprise documentation is notoriously outdated, contradictory, and poorly maintained. By forcing AI agents to ingest and respect this cross-system context deterministically (without an LLM to dynamically evaluate the *quality* or *relevance* of that context), `teamctx` risks actively degrading agent performance. Instead of writing good code, agents will be paralyzed by conflicting "truth" cards generated from deprecated specs and abandoned Jira tickets that nobody bothered to close.