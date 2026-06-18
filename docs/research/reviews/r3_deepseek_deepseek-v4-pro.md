I’m going to cut straight to the decisions. The live disagreements are trivial relative to the crux, so I’ll adjudicate them fast, then settle the existential pivot.

### Live disagreements – pick a side

**D1: signal/noise – NO ML.** Programmable blast-radius rules (`.teamctx.yaml`) only.  
*Why:* Determinism is the one thing that makes a policy gateway auditable, debuggable, and trustworthy. Adding ML turns every decision into a probability that every SOC-2 auditor will reject and every developer will game. The product’s differentiation is *provable* correctness; you don’t rank with ML, you define exact policies.  
*I disagree with Model‑B (who pushed smart‑edge ML/LLM)* – that suggestion confuses a relevance engine with a policy engine, and would kill the enterprise sale instantly.

**D2: Ambara – KILL entirely.** Not a “defer,” not a “policy‑only graph.”  
*Why:* Ambara is a data‑warehouse conceit that consumes team bandwidth and confuses the value prop. The pivot is to an active enforcement plane; a historical knowledge graph is neither necessary nor helpful. The risk of having Ambara anywhere in the roadmap is that the team keeps “context broker” brain and fails to execute the hard real‑time gateway.  
*I disagree with Model‑C (the “defer as strict policy‑only graph” compromise)* – that’s a half‑kill that wastes attention and keeps the old identity alive. Delete the repo, close the issues, remove it from all slides.

**D3: wedge – enterprise POLICY‑BLOCK is the only one that opens budget.** Prevented‑rework is a nice metric but not a decision‑trigger. A CISO doesn’t sign a PO because a tool might reduce refactor collisions; she signs when you say “an AI agent cannot push code unless the linked ticket has the ‘security‑reviewed’ label, and I can prove it in an audit.” The hard block, at a choke‑point, is a compliance artifact.  
*Disagree with Model‑D (the prevented‑rework proponent)* – that story works for DevTools sold to ICs, not for a control‑plane sold to platform security teams.

---

### Resolving the crux – active gateway vs. passive evidence broker

**1) Does becoming the gateway break the founding invariants?**  
Yes. It explicitly breaks:  
- **“Cannot act”** – you now *actively* block pushes, reject PRs, lease files.  
- **“Cannot track”** – every check and decision is logged, because that is the audit trail enterprises buy.  
- **“Incapable of harm”** – a misconfigured policy can block legitimate emergency fixes; that *is* harm, mitigated by overrides and fail‑safe design, but not “incapable.”  

The other invariants – deterministic, cross‑agent – remain. Read‑only gets fuzzy, but we’re not mutating code; we’re interposing on mutation operations, so we’re more “control‑plane” than “read‑only.”  

**Is that acceptable?** Yes, because we are no longer building a passive tool for invididual developers; we’re building a compliance‑enforcing proxy for enterprises. The original invariants were designed for a different product. Holding onto them after the repositioning would be a mistake. We keep determinism (the true enabler) and shed the rest.

**2) Passive evidence‑broker vs. active policy‑gateway – which is v1?**  
Active policy‑gateway. Passive context cards are a feature inside the gateway, not a product. The buyer for passive‑only is a team lead with no budget who can already script something; the buyer for the gateway is a VP of Engineering or CISO who needs auditable control over AI‑generated code. V1 must be the gateway.

**3) Single point of failure + surveillance – reconcile.**  
- **SPOF**: The gateway must be distributed and fail‑open for read‑only context (so agents still get standard context if the gate is down) but fail‑closed for write actions (block on gateway outage), with a documented emergency break‑glass (temporary admin‑override API that logs the waiver). This is exactly how API gateways work in prod.  
- **Surveillance**: We don’t spy on humans; we spy on *agents* on behalf of the enterprise. The log is a compliance asset, not employee monitoring. Positioning matters: “audit immutability” not “surveillance.” The original product wanted to avoid surveillance for dev‑trust; we now target a different user – the buyer wants surveillance of agents. So the value overrides the original ethical stance.

**4) Can we mediate writes and still be “incapable of harm”?**  
No. A gate that can block can also block incorrectly and halt legitimate work. Accept that, and build harm‑reduction: deterministic, git‑traceable policies; dry‑run mode to preview blocks; fast policy change propagation; emergency bypass with full logging; and a strict “least‑privilege” approach so that a misconfigured policy doesn’t block everything. The guarantee becomes *“harm is auditable and reversible,”* not *“harm is impossible.”* That’s the right trade for the buyer.

---

### FORCED DECISION: exact v1, design partner, north‑star metric, pricing

**V1 scope (90 days) – ONE paragraph:**

`teamctx` ships as a deterministic **Agent API Gateway** that intercepts every coding‑agent write (commit, PR, branch push) to GitHub/GitLab and issues queries to Jira. It enforces a single, hard‑coded policy: the agent’s O‑Auth‑impersonated user must have write access on the target repo (via group mappings), and the linked Jira ticket must carry a pre‑configured label (e.g., `security‑approved`). If either check fails, the gateway returns a blocking response with a prescriptive error message (no ML, no probability). All decisions are logged to an append‑only audit store, served to the agent via MCP protocol. There is no Ambara, no data‑warehousing, no ranking. The two connectors are **GitHub** (or GitLab) and **Jira**. MCP‑only; no CI‑plugin, but the gateway posts a blocking commit status on the PR so existing CI is gated indirectly.

**First design‑partner profile:**  
A mid‑large Fin‑tech firm (250‑500 engineers, SOC‑2/PCI) that already allows GitHub Copilot/Cursor and has internal platform engineering. The check‑signer is the **Head of Platform Security**, who needs an auditable way to prove that agent‑generated code never bypasses the mandatory security‑review label on stories. Team size: the buyer’s group owns the agent toolchain (~10 platform engineers). The deal hinges on a live pilot showing a single blocked violation during a simulated audit.

**The ONE north‑star metric:**  
**“Policy‑enforced agent actions per month”** – i.e., the number of agent write‑attempts flowing through the gateway where a policy decision was made (allow or deny). This measures both adoption and value: a linearly growing count means more agents are gated and the enterprise is relying on the gate. (Audit coverage is derived from this; if it’s 0, nothing is gated.)

**Pricing wedge:**  
- **Free tier:** up to 5 developers, community support, GitHub+Jira connectors, basic label‑check policy (only `security‑approved`). This is a developer‑friendly onboarding wedge that creates internal champions.  
- **Enterprise:** per‑developer per month, starts at $30/seat/month (annual). Opens advanced policy (custom `.teamctx.yaml` rules, multiple label requirements, time‑based expiry, CI‑stage checks), SAML/OIDC, priority support, and an auditable admin dashboard. No per‑agent‑call pricing; that would penalize high‑frequency usage and is unpredictable for buyers. This positions teamctx as a control‑plane subscription like a security SaaS, not a metered utility.

The company now bets everything on becoming the **deterministic policy choke‑point for AI‑assisted coding**. That’s v1. Ship it.