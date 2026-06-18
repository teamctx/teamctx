**R1: SIGNAL/NOISE -> Task-scoped deterministic relevance + optional smart edge**
*   **BREAK:** "Task-scoped" sounds easy in a pitch, but architecturally, calculating "touches the same file" synchronously at the moment of agent invocation is a death sentence. GitHub API rate limits will throttle you instantly if you poll for open PR diffs every time an agent wakes up. Furthermore, "touches the same file" is a naive heuristic; changing an interface in `types.ts` breaks `api.ts` even if `api.ts` isn't touched.
*   **STRENGTHEN (Architecture):** You cannot rely on synchronous API calls to systems-of-record. You must build a **streaming materialized view** of repo state. The enterprise deployment requires a webhook-ingestion pipeline (e.g., Kafka/Redpanda -> fast local KV store like Redis/Dragonfly) that constantly maintains an index of `Open PRs -> Touched Files / AST Symbols`. When the agent queries teamctx via MCP, it hits this local cache in <10ms. 
*   **STRENGTHEN (The "Smart Edge"):** Do not build a "smart edge" ranking layer. That dilutes your "no-LLM" invariant and introduces non-determinism right where the user feels it. Instead, make relevance programmable. Ship a `.teamctx.yaml` specification where teams define deterministic blast-radius rules (e.g., `if branch_touches: src/auth/** -> require_linked_issue_label: security-review`). Let the team define the noise floor.

**R2: GARBAGE-IN -> Broker asserts CHANGE + PROVENANCE + FRESHNESS, not truth**
*   **STRENGTHEN (Product):** This is a massive upgrade. Re-framing stale data from a bug into a "Delta-worth-checking" is brilliant. It shifts the burden of truth to the human/agent, keeping the broker mathematically pure.
*   **STRENGTHEN (Architecture):** To assert deltas, you must track the high-water mark of the developer's current session. The broker needs a local state mechanism (a local SQLite DB for the solo dev; a Redis session store for enterprise) that records `(user, branch, base_commit_hash, timestamp_of_branch_creation)`. 
*   **STRENGTHEN (Payload Design):** The MCP payload to the agent must be aggressively structured to force agent behavior. Do not return markdown. Return JSON schemas that trigger tool-use. Example: `{"event": "upstream_mutation", "entity": "JIRA-412", "mutation_time": "T+4hrs from branch creation", "fields_changed": ["acceptance_criteria"], "action_required": "fetch_latest"}`. This deterministically forces the LLM to realize its context window is poisoned and fetch the new state.

**R3: MOAT -> Stack (Neutrality x Safety x Permission depth) > Determinism**
*   **BREAK:** Neutrality ("Switzerland") is a weak moat. Switzerland gets invaded when the stakes are high enough. GitHub/Microsoft will eventually build a cross-system context graph for Copilot. 
*   **STRENGTHEN (The Real Moat):** Your durable moat is **Identity Resolution and Permission Mapping**. Connecting Jira to GitHub is easy. Mapping `Jira Group: Backend-Eng` to `GitHub Team: backend-core` to `Confluence Space: Architecture` under a single, impersonated developer identity is an enterprise nightmare that nobody wants to solve. If teamctx becomes the universal translator for IAM across the SDLC, you are un-rippable. 
*   **STRENGTHEN (GTM):** You are not selling a context tool; you are selling an **Agent Firewall**. CISOs are terrified of agents running amok with god-mode service accounts. Your moat is that teamctx inherits the *exact* OAuth/OIDC permissions of the human developer invoking the agent, dynamically stripping out payloads the developer shouldn't see. You win because you are the only safe way to deploy an agent.

**R4: WEDGE -> Prevented-rework ROI (Demo: parallel open PR changes API)**
*   **BREAK:** "Prevented rework" is a lagging indicator. You cannot definitively prove to a CFO that you saved 3 hours of work because the work never happened. Developers will say "I would have caught that anyway."
*   **STRENGTHEN (The Demo):** The parallel PR demo is good for developers, but it doesn't open enterprise wallets. You need a dual-wedge demo.
    *   *Dev Wedge Demo:* The parallel PR collision (as you described). It drives bottom-up adoption.
    *   *Buyer Wedge Demo (Platform Eng/CISO):* Show an agent trying to modify a SOC2-compliant file (`auth.go`). teamctx intercepts the MCP request, checks the linked Jira ticket, sees it lacks the `security-approved` label, and returns a hard deterministic block: `{"error": "policy_violation", "reason": "auth.go requires security-approved label on linked ticket"}`. The agent is forced to tell the developer to get approval. *This* sells the enterprise deal instantly. It proves safety.

**R5: AMBARA -> Defer to strict artifact/policy-only graph**
*   **BREAK:** Kill Ambara. Do not defer it. Do not put it on a roadmap. It is a distraction that muddles your messaging. You are building a high-speed, deterministic, stateless (or ephemeral-state) routing and policy engine. A "collective memory graph" implies durable storage, complex querying, and analytics. It directly contradicts your "Privacy / can't track" promise, no matter how much you claim it's artifact-only. 
*   **STRENGTHEN:** Focus 100% of your engineering cycles on connector depth, low-latency webhook ingestion, and rock-solid MCP adapters. If teams want a graph, let them export teamctx logs to Datadog or Snowflake. You are the pipes, not the data warehouse.

---

### (A) THE SINGLE HIGHEST-LEVERAGE CHANGE

**Pivot the core identity from "Context Broker" to "Agent API Gateway" (The Kong/Apigee for AI Agents).**

"Context" sounds like a nice-to-have vitamin that improves prompt quality. An "API Gateway" is fundamental infrastructure. 

If you look at how microservices evolved, we didn't let every service talk directly to every other service; we put an API Gateway in the middle to handle routing, rate-limiting, auth, and policy enforcement. AI Agents are the new microservices. They are currently wildly insecure, hitting APIs directly with massive context windows.

By positioning teamctx as the Agent API Gateway (via MCP):
1.  **You own the choke point:** Every agent must route through you to touch a system of record.
2.  **You solve the CISO's nightmare:** You provide a single pane of glass for audit logging exactly what context every agent requested and received.
3.  **You commoditize the agents:** If teamctx holds the integration logic, the permission mapping, and the policy enforcement, the LLM agent becomes a swappable compute engine. You own the high-margin enterprise integration layer; they fight a race-to-the-bottom on inference costs.

**Architectural implication:** You must build teamctx as a high-performance proxy. It needs to support middleware plugins (e.g., a rate-limiter middleware, a PII-redaction middleware, a Jira-auth middleware).

---

### (B) THE ONE THING STILL MISSING: The "Cold Start" Intent Resolution

You have built a brilliant engine for fetching context *once you know what the developer is doing*. But how does teamctx deterministically know what the developer is doing at the exact millisecond the agent is invoked?

**The Blind Spot:** Developers are lazy. They do not meticulously link Jira tickets to branches before they start coding. They branch off `main`, name it `fix-login-bug`, and start typing. 

If teamctx relies on explicit system-of-record links (e.g., a Jira ID in the branch name, or a pre-existing PR) to fetch context, it will suffer from a massive "Cold Start" problem. For the first 4 hours of a task, before a PR is opened or a commit is pushed, teamctx will have zero context to provide, rendering it useless during the most critical generative phase of the work.

**The Concrete Fix (Architecture & UX):**
You must build a deterministic **Local Intent Resolver** that runs on the developer's machine (as part of the MCP daemon) before hitting the network.

1.  **Branch Name Parsing:** Regex extraction of ticket IDs from branch names (e.g., `git checkout -b JIRA-123-fix-auth`). This is standard, but brittle.
2.  **Local State Sniffing:** The MCP daemon must read the local `.git/config` and `.git/HEAD` to instantly know the current branch, the base commit, and any uncommitted modified files. 
3.  **The "Interactive Handoff" (Crucial):** If the Local Intent Resolver cannot find a deterministic link to a system-of-record (e.g., branch name is just `fix-stuff`), teamctx must *intercept* the agent's first action and force a prompt back to the human. 
    *   *Agent:* "I'm ready to code."
    *   *teamctx intercepts, injects payload to Agent:* `{"status": "missing_intent", "action": "ask_user_for_ticket_id"}`
    *   *Agent to Human:* "Before I start, what Jira ticket or Confluence spec are we working against?"

You must solve the Cold Start problem deterministically. If you assume the systems-of-record are perfectly linked to the local dev environment at minute zero, your hit rate for useful context will be abysmal, and developers will uninstall the tool before they experience the "prevented rework" magic.