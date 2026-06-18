D1 — ML at the edge vs pure deterministic rules
-----------------------------------------------

I’m siding with **(b) NO ML in the core** for v1 and the near term.

Where I **disagree with the pro-ML takes (e.g. Anthropic-style “just bolt on a small reranker”)**:

- This is a *policy* product, not a retrieval product. The core value is: “I can tell you exactly why the agent saw X and not Y.” The moment you let an opaque scorer influence which files/issues get surfaced, you’ve polluted the audit trail. A “thin” ML layer is still non-deterministic from the auditor’s perspective.
- “Smart ranking at the edge” sounds nice, but it drags you into all the complexity: feature drift, monitoring, re-training, blame when the reranker hid the one file that mattered. That’s surface area without wedge.
- Teams *already* want to write codified change-policy: “only touch files under src/payments if Jira ticket has component=payments”; “never recommend editing authz/ without security-approved label.” Those are inherently deterministic blast-radius rules. These are programmable, testable, and CI-able.

The right model:

- Core: **.teamctx.yaml** (or repo/org-level policy) is the *only* arbiter of relevance and permission. Pure rules: path/glob, labels, components, review history, ownership.
- If later you want “nice to have” ML ranking of *already-authorized* cards for UX, put it on the *client side*, clearly labeled “non-policy hinting,” and don’t feed it back into the enforcement decisions. That’s a v3 problem.

So: **v1 is 100% deterministic, programmable relevance. No ML in the control plane.**

---

D2 — Ambara: kill or defer?

Ambara as originally pitched (“our own cross-tool knowledge graph / warehouse”) should be **killed, not deferred**.

Where I **disagree with the defer crowd (e.g. “keep a small policy graph only” à la OpenAI/Claude thinking)**:

- The moment you say “strict policy-only graph,” you’re 2 decisions away from: “well, while we have the graph, we may as well do analytics / heuristics / discovery.” You’ve re-opened the data-warehouse rabbit hole.
- There is *no* incremental wedge there: every SOC2-lite vendor, internal data platform, and AI security proxy is already trying to build some “graph of who can see what.” Your advantage is not “a graph” but “we sit in the invocation path, under per-user impersonation, and enforce.”
- Also: Ambara’s mental model (“we store all your org state forever”) is in direct tension with the original invariants (minimize data retention, minimize tracking, avoid being a surveillance substrate).

What’s acceptable:

- Yes to **event-sourced materialized views** strictly as an implementation detail of the PDP: inbound webhooks from Jira/GitHub/Confluence -> log -> compacted materialized cache keyed by identity+resource for fast decisions. That’s **not** “Ambara the product.”
- No user-facing “org graph” product, no BI layer, no “run queries over all your history.”

So: **Ambara as a named project and product concept is dead. Only keep the minimal, local event store necessary to answer policy questions.**

---

D3 — Is prevented-rework enough, or is policy-block the only real wedge?

Prevented rework is *nice*, but not budget-creating.

I’m with the “**enterprise POLICY-BLOCK is the budget wedge**” side and disagree with the “rework-as-primary-wedge” argument (e.g. OpenAI-ish “productivity ROI is enough”).

Why:

- “We prevent bad refactors / parallel-PR collisions” is developer tooling candy. It wins you love, not big checks. It’s also squishy to prove: “we *would* have had 2 weeks of rework if not for you” is unprovable counterfactual.
- “We hard-block AI from touching auth.go unless XYZ security label approved” is a clear governance and risk story. That’s how budgets get signed: “we are enabling AI coding without expanding our blast radius.”
- The same mechanism (policy-block) *implies* rework prevention as a side-effect: fewer bad changes merged, fewer revert trees. You don’t need to sell that as the primary value; it becomes supporting evidence.

So the wedge that opens doors is: **“we are your PDP/PEP for AI-driven code and infra changes; your company policy is mechanically enforced on every AI-driven write.”** Rework reduction goes in the pitch deck, not the pricing model.

---

The crux: Does becoming an enforcement gateway break the founding invariants?

You *are* changing the product class. Some invariants break; some you keep.

1) Which invariants break, and is that acceptable?

Original invariants:

- Read-only  
- Cannot act  
- Cannot track  
- Deterministic  
- Cross-agent  
- “Incapable of harm”

If you become a gateway that can **block writes, lease files, gate CI**, here’s the reality:

- **Read-only:** broken. You are now influencing write paths (e.g., returning “DENY” to an agent trying to modify a file, setting a lease flag in your own store, toggling a CI check).  
  - This is **acceptable**; “read-only” was never compatible with being a proper PEP. You can still be “write-minimizing” (writes only to your own control state, never to customer systems).
- **Cannot act:** broken. “Deny this write” *is* an action. So is “fail this CI check” or “refuse to open a PR.”  
  - Again, acceptable *if* every action is a pure function of an auditable policy on auditable inputs and is **reversible** by a human override.
- **Cannot track:** partially broken. A gateway inevitably sees access patterns.  
  - You can constrain this: log only **decision facts** (“user U, resource R, policy P, ALLOW/DENY, rationale”), with configurable retention and opt-out for per-file read-logging. But yes, you are now *capable* of building a surveillance substrate. You need governance and defaults to *not* become that.
- **Deterministic:** preserved and now more critical. Every decision must be reproducible from state+policy+request. No heuristics in the control path.
- **Cross-agent:** preserved and strengthened: one PDP/PEP for *all* AI tooling and CI components.
- **Incapable of harm:** strictly speaking, broken. If you can deny writes, you can cause outages (block hotfixes, slow incidents). That’s a kind of harm.

You need to **reframe** the invariants:

- Old: “incapable of harm”  
- New: **“incapable of *unbounded or opaque* harm.”**  
  - Every deny is explainable.  
  - There is always a human bypass path defined by the customer.  
  - You **never** mutate customer artifacts directly; you only gate / annotate / block.

If you try to cling to strict “read-only/cannot act,” you are building a passive index that others will route around.

2) Passive evidence-broker vs active policy-gateway — which is v1?

v1 must be the **active policy-gateway**.

The passive evidence broker is a feature inside a bigger product: it’s useful but easy to clone, hard to charge for, and low in the priority stack for buyers. Also:

- Dev tools buyers already have: code search, code intelligence, doc search, repo graph. A “smarter contextualizer” is marginal.
- CIO/CISO/Head of Eng **does not care** about your context relevance. They care about: “what is my blast radius if I let AI write code?” That’s a policy question, not an evidence question.

So:

- v1 = **minimal, deterministic PDP/PEP for AI-driven writes**, with just enough “context card” functionality to prove that decisions are grounded in correct identity+permissions.
- The passive cards-only product by itself is not a company. It’s an open-source sidecar at best.

3) Single point of failure and surveillance substrate — reconcile or refute?

You *are* a single point of failure in the decision path. Pretending otherwise is dishonest.

Reconciliation:

- **Single point of failure:**  
  - De-risk with explicit modes:
    - **Fail-closed**: security-critical repos/paths (e.g., auth/, payments/). If PDP is down, AI writes are blocked; humans can still push manually.  
    - **Fail-open**: low-risk areas (docs, internal tools) where PDP downtime just bypasses enforcement.  
  - Provide a **local fallback mode**: if the central PDP is unreachable, agents can fall back to last-known-OK policies cached locally for a limited time window, with audit flags.
- **Surveillance substrate:**  
  - You can’t avoid being *capable* of surveillance, but you can architect *against default abuse*:
    - Default: log **decisions**, not full request payloads. No full code bodies, no prompts, no token-level traces.  
    - Optional “deep audit” mode with explicit DPA and shorter retention.  
    - On-prem/self-hosted by default for any serious customer; no centralized SaaS log aggregation by you unless explicitly requested.  
    - Clear, tenant-controlled retention + redaction knobs.

If someone is allergic to any central PDP, they’re not your customer. You’re building the *policy choke point*; that’s inherently centralizing. The job is to make that palatable to a CISO, not to eliminate centralization.

4) Can it mediate writes/leases/blocks and still be “incapable of harm”?

No, not under the old definition. Under a *reframed* definition, yes.

- If “harm” means:
  - corrupting customer data,  
  - silently widening access beyond policy, or  
  - making non-auditable decisions,  
  then you can still be “incapable of that harm.”
- You *cannot* be incapable of productivity harm: false positives/denies, delays in urgent changes, friction for engineers. That’s inherent to any guardrail.

So you should explicitly **kill “incapable of harm”** as a slogan. Replace it with:

- **“Incapable of unauthorized change.”**  
- **“Every denial is explainable and overrideable.”**

That’s both honest and aligned with the PDP/PEP posture.

---

Forced decisions

### 90-day v1 scope (one paragraph)

v1 is an **active AI policy-gateway for code changes**, not a passive context broker. In 90 days, you ship: (1) a deterministic PDP/PEP that sits between AI coding agents (via MCP) and GitHub, enforcing **per-user, impersonated, repo/branch/path-level policies**; (2) **GitHub** and **Jira** as the only connectors: identity-resolution maps “who is this human behind this agent call?” and “which Jira ticket authorizes this change?”; (3) policy as code in a `.teamctx.(yaml|rego)` file committed to the org’s infra repo, defining blast-radius rules and ticket-label gates; (4) MCP server that tools like Claude/Codeium/Devin/etc. call for both read-context (cards) and write-authorization (can I edit these files? can I open this PR?); (5) a **GitHub App integration into CI** that adds a required “AI Policy Check” status on PRs, deny/allow based on policy and linked Jira issue, but **no direct writes to repos** (only block/annotate via checks). No Confluence, no GitLab, no Ambara, no ML, no fancy analytics — just policy-coded read scoping + deterministic write gating for AI-generated code.

### First design-partner profile

One profile:

- **Company:** 200–800 engineers, B2B SaaS or fintech, ~50–200 microservices, heavy GitHub + Jira usage, at least one security or platform team *already drafting AI usage policies* but lacking enforcement.  
- **Shape:** Single primary product org with 3–6 platform/security leaders who own SDLC governance; AI coding tools are being piloted or rolled out (e.g., GitHub Copilot, Claude for code, or internal AI pair program).  
- **Signer:** **Head of Engineering or VP Platform** with a Security Engineering counterpart; budget comes from “AI enablement / SDLC modernization,” not from raw infra. The person actually pushing the deal is a Director of Platform or DevX tasked with “enable AI coding safely.”

You do *not* start with a 10-person startup or a FAANG; too small = no policy pain, too big = six-month procurement.

### Single north-star metric

One metric:

- **“% of AI-originated code changes that are evaluated and enforced by teamctx.”**

More precisely: 

> `NSM = (# of PRs with AI-generated content where teamctx’s “AI Policy Check” ran and produced a non-N/A decision) / (total # of PRs with AI-generated content in the org)`

The goal: in a design partner, get this to **>80%**. This captures both coverage (are we on the AI paths?) and actual usage (are teams wiring their agents/CI through you). Everything else (blocks, policy complexity, rework saved) is secondary diagnostics.

### Pricing wedge

You need an obvious **free/dev tier** to avoid being blocked from experiments, but the money is in per-engineer governance.

My recommendation:

- **Free tier:**
  - Self-hosted or single-tenant SaaS for up to **20 engineers**, 1 org, 1 environment, limited log retention (e.g., 7 days).  
  - All core features: GitHub+Jira connectors, MCP server, CI check, `.teamctx` policies. No support SLAs.  
  - Purpose: let the Head of Eng’s “AI tiger team” wire you into a pilot without asking for budget.
- **Paid: per governed developer seat**, not per agent call.  
  - “Governed seat” = any human whose AI-assisted PRs are subject to teamctx checks.  
  - Pricing ballpark: **$25–$40 per governed dev/month** to start; enterprise discounts at scale.  
- **Enterprise SKU:**  
  - Adds SSO/SAML, audit log retention controls, multi-org/multi-env policies, dedicated support, and on-prem deployment support.  
  - Still per-seat, but with annual commit and a minimum (e.g., $25k/year).

Per-agent-call or per-token pricing is a trap; it pushes you into “LLM infra” territory and feels like metering safety. You’re selling **AI governance for developers**, which maps cleanly to “per governed engineer.”

---

Summary of hard stances:

- **No ML in the deterministic core**; everything is policy-as-code.  
- **Ambara is dead as a product**; only keep minimal event-sourced state for PDP decisions.  
- **Wedge is enterprise policy-block**, not “prevented rework” as primary.  
- **v1 is an active AI policy gateway** for GitHub+Jira via MCP and CI, not a passive context card broker.  
- You **accept** being a central enforcement point; you mitigate, not eliminate, SPoF/surveillance risk.  
- You **drop “incapable of harm”** and instead promise “incapable of unauthorized change, fully auditable, always overrideable.”