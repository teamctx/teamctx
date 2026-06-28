### 1) WHAT KILLS THIS: Top 3 risks/blind spots

*   **The "No IDE Plugin" Stance:** You are building a context engine for coding agents but refusing to live where the coding happens. If a developer has to run a CLI command or check a separate terminal window before hitting `Cmd+K` in Cursor or Copilot, your adoption will be zero. Developers will not context-switch to fetch context. 
*   **Alert Fatigue / The Monorepo Problem:** "An open PR touches this same file" is useless noise in a large codebase. Deterministic rules lack semantic filtering. If you emit a card every time a shared utility file is touched, developers and agents will learn to ignore your cards within 48 hours. 
*   **Integration Hell & Schema Chaos:** "Source-location-agnostic connectors" is a naive underestimation of enterprise reality. Jira isn't a standard; it's a bespoke, heavily mutated database for every company. If your deterministic broker relies on mapping custom fields, webhooks, and status transitions across 50 different enterprise Jira/GitLab configurations, your gross margins will be destroyed by implementation services.

### 2) THE DETERMINISM BET: Is 'no-LLM' a durable moat?

It is not a moat; it is an optimization for a temporary constraint (token cost/limits). 

*   **The Steelman against you:** Context windows are hitting 1M+ tokens, and inference costs are plummeting. Within 18 months, the default behavior won't be "carefully fetch 4 deterministic context cards." It will be "dump the entire Jira epic, the last 10 merged PRs, and the Confluence space into the prompt and let the LLM sort it out." 
*   **Semantic vs. Lexical:** A deterministic engine says "Acceptance Criteria changed." An LLM says "Acceptance Criteria changed, *and it directly contradicts the logic you just wrote in `auth.ts`*." Your broker leaves the hardest part, synthesizing the *meaning* of the change, to the downstream agent, which might miss it without the full text.
*   **Brittleness:** Deterministic systems break when APIs or human workflows change. LLMs are fuzzy but highly resilient to messy, unstructured human data. 

### 3) WEAKEST WEDGE: Safety boundary

"Safety boundary against prompt injection" is a theoretical vitamin. You are solving a problem CTOs do not yet have budget for. 

*   **Nobody pays for AI supply chain safety (yet):** No Engineering VP is losing sleep over a malicious payload hidden in a Jira ticket description hijacking an AI agent. They care about shipping features. Security might think it's neat, but they won't champion a devtool.
*   **Who pays FIRST:** Engineering Directors pay for **Promise 1 (Prevented Rework)**. If you can prove that `teamctx` stops an agent from hallucinating a 3-hour refactor because it didn't know an API contract was updated in a parallel PR, you have a hard ROI. 
*   **The Wedge:** Sell velocity and reduced token-burn to Eng Leaders. Let the security/privacy promises be the grease that gets you through InfoSec procurement, not the tip of the spear.

### 4) AMBARA vs PRIVACY: The collective graph tension

Ambara is fundamentally at odds with your "can't track / privacy-first" promise. 

*   **The Oxymoron:** You cannot build a "durable collective memory" of team coordination without inherently mapping who is doing what, when, and with whom. The graph *is* the tracking. 
*   **Enterprise Permissions are Dynamic:** If Ambara remembers a technical decision made in a private repo, and a developer later loses access to that repo, does Ambara dynamically scrub or mask that node in the graph? If not, it's a massive data exfiltration risk. If yes, the graph becomes Swiss cheese and computationally heavy to serve.
*   **Kill it for now:** Ambara dilutes the brutal simplicity of the stateless `teamctx` broker. It turns a sharp, fast utility into a heavy, stateful knowledge management platform. Drop it until the broker is indispensable.

### 5) DAY-IN-THE-LIFE: The single most important thing to nail

*   **For the Solo Builder:** **Zero-friction MCP (Model Context Protocol).** It must act as an invisible daemon. If they have to write a script to pipe your output into Claude Desktop, you lose. It needs to be a single binary they run that instantly exposes your context cards as native MCP tools to whatever agent they already use.
*   **For the Enterprise:** **Real-time, impersonated OAuth.** If `teamctx` requires a Jira/GitHub Admin to provision a "god-mode" service account that reads everything, InfoSec will block it. It must strictly inherit the exact read-permissions of the developer invoking it at that exact millisecond.

### 6) BLIND SPOT: The "Garbage In" reality of Systems of Record

Your entire thesis assumes that Jira, Confluence, and PR descriptions contain the *truth*. 

As an experienced operator, I can tell you they don't. Jira tickets are notoriously outdated. Confluence is where documentation goes to die. PR descriptions often just say "fixes bug." 

If your deterministic broker treats these artifacts as "source-backed evidence" and feeds them to an agent, you will confidently inject outdated, incorrect context into the workflow. LLMs are currently used to *infer* intent precisely because explicit human artifacts are so unreliable. If your system cannot detect *stale* or *conflicting* documentation without an LLM, it will actively degrade the agent's output.