**D1: Signal/noise (ML edge vs. NO ML)**
I completely disagree with GPT-4 and Gemini here. They are infected by the current AI hype cycle and want to bolt "smart ML ranking" onto the edge. That is a fatal mistake. The entire premise of this company is *deterministic, auditable access*. The second you introduce an LLM or ML classifier to rank or filter context, you become a black box. You lose the CISO. You lose the trust. Relevance must be 100% PROGRAMMABLE via deterministic blast-radius rules (`.teamctx.yaml`). If the coding agent wants to do semantic filtering on the payload, let the agent burn its own tokens to do it. You are the secure pipe; pipes don't guess what water you want. 

**D2: Ambara (Kill vs. Defer)**
Claude is hedging by suggesting you "defer" Ambara as a strict policy graph. I say KILL it entirely. You are a seed-stage startup with 90 days to prove a wedge, not a research lab building a proprietary graph database. You are building an event-sourced materialized view on top of existing systems of record. Adding a bespoke graph DB layer is an architectural vanity project. Rip it out of the codebase today.

**D3: The Wedge (Prevented-rework vs. Policy-block)**
Llama's belief that "prevented rework" is provable enough to sell is a naive PLG fantasy. Developers do not pay for tools, and Engineering Managers cannot quantify "prevented rework" well enough to justify a new line item in this macro environment. The ONLY wedge that opens enterprise budget is the **POLICY-BLOCK**. CISOs and VPs of Engineering are terrified of autonomous agents committing unreviewed, non-compliant code. You sell them a deterministic firewall that physically prevents an agent from merging a PR touching `auth.go` unless the linked Jira ticket has a human-applied `security-approved` label. Fear buys software; rework prevention is a nice-to-have vitamin.

***

**THE CRUX: Passive Evidence Broker vs. Active Enforcement Gateway**

Your founding invariants ("read-only", "cannot act", "incapable of harm") were wrong. They were academic safety blankets. Startups pivot. You must abandon them to build a real business.

1) **Does becoming the gateway break invariants?** Yes. It shatters "read-only" and "cannot act." You are now gating CI and enforcing leases. Is that acceptable? Absolutely. You are trading the useless invariant of "incapable of harm" for the highly lucrative invariant of "provably auditable." 
2) **Which is V1?** The Active Policy-Gateway. A passive evidence broker is just a glorified search API. Nobody pays $100k ARR for a search API. They pay $100k for an Agent Firewall that keeps them SOC2 compliant when 500 developers are using Cursor.
3) **SPOF and Surveillance Substrate:** Stop apologizing for being a SPOF. Okta is a SPOF. GitHub is a SPOF. If you are valuable to an enterprise, you are in the critical path. As for the "surveillance" aspect: developers hate being surveilled, but they *do not care* if you surveil the AI. In fact, they want you to. You are logging the *agent's* reads and actions, not the human's keystrokes. 
4) **Mediate writes and remain 'incapable of harm'?** No. You drop "incapable of harm." If you block a critical hotfix because of a misconfigured policy, you caused harm. Welcome to enterprise infrastructure. You mitigate this not by being "incapable" of action, but by being instantly reversible, transparent, and deterministic. 

***

**FORCED DECISIONS**

**EXACT v1 (90-day) Scope:**
You are building the Active Gate. The scope is an event-sourced, local-cache MCP server for the agent, paired with a CI/CD webhook blocker. Exactly TWO connectors: GitHub and Jira. No Confluence, no GitLab. The agent queries the MCP server to read Jira/GitHub state (impersonating the human dev's OAuth token to guarantee exact read perms). When the agent attempts to push/PR, the teamctx CI webhook evaluates a deterministic `.teamctx.yaml` policy file (e.g., "Block PR if touching /billing without Jira label 'finance-approved'"). If it fails, teamctx hard-blocks the CI pipeline. 

**The SINGLE First Design-Partner Profile:**
A Series C/D B2B SaaS company, 150-300 employees, ~100 engineers. They are SOC2/HIPAA regulated. They have widely deployed Cursor or GitHub Copilot and are experimenting with autonomous agents (Devin/Sweep). The buyer who signs the check is the VP of Engineering or CISO who is actively losing sleep over AI-generated code bypassing compliance controls.

**The ONE North-Star Metric:**
Number of AI-generated PRs/commits actively evaluated (and potentially gated) by teamctx policies per week. (This proves you are embedded in the critical path of their SDLC).

**The Pricing Wedge:**
Enterprise Gate model. NO free tier. Do not waste time with tire-kickers. $1,500/month base platform fee (covers the integrations and the PDP/PEP engine) + $20 per human developer seat. You do not charge per-agent-call because you want the agents to query you constantly without penalty to ensure freshness.