**DISAGREEMENTS**

- **Echo** (the “smart‑edge ML ranking” camp) is wrong: feeding an LLM outside the deterministic core re‑introduces the very nondeterminism we built to avoid.  
- **Nimbus** (the “keep Ambara, just defer” camp) is wrong: a policy‑only graph without enforcement is a dead‑weight feature that will never move the needle.  
- **Orion** (the “prevent‑rework proof‑point sells” camp) is wrong: buyers only pay for a *budget‑blocking* lever, not for a nice‑to‑have audit of “no‑rework”.  
- **Helix** (the “passive‑only evidence broker is the safe bet” camp) is wrong: the market signal is that enterprises will not adopt a read‑only pipe when they need a hard gate on risky changes.

---

## 1. Do we break the founding invariants by becoming a choke‑point?

| Invariant | Broken? | Why it’s acceptable (or not) |
|-----------|---------|------------------------------|
| **Read‑only** | **Yes** – we will now issue *deny* decisions and lease tokens. | The original read‑only promise was a risk‑mitigation for early adopters. Once we add enforcement we must **re‑brand** as a *Policy Enforcement Plane* (PEP). The old invariant is retired, not violated. |
| **Cannot act** | **Yes** – we will block pushes, gate CI, and issue lease tokens. | Action is the value proposition; we simply shift the “cannot act” clause to a *controlled* act (deterministic PDP/PEP). |
| **Deterministic** | **No** – the PDP remains a pure function of the policy graph and request context. | This is the moat; we keep it intact. |
| **Cross‑agent** | **No** – we still sit between GitHub, GitLab, Jira, Confluence, CI. | Unchanged. |
| **Incapable of harm** | **Partially** – any deny could be a *false positive* that blocks a legitimate developer. | Harm is now a product‑risk we must manage via **audit logs, explainability, and an override path**. The invariant is softened but not eliminated. |

**Conclusion:** The only invariants we can keep are *determinism* and *cross‑agent*. The others must be deliberately abandoned and re‑framed as “controlled‑action” guarantees. That is acceptable because the market demand is for *hard* enforcement, not for a passive data feed.

---

## 2. Passive evidence broker vs active policy gateway – which is v1?

The **active policy gateway** is the only product that creates a defensible revenue stream and a clear competitive moat. A passive broker can be built later as a “read‑only side‑car” for compliance reporting, but it does **not** solve the wedge problem (budget‑blocking). Therefore:

**v1 = Active Policy Enforcement Plane (PEP) with deterministic PDP, audit logging, and lease issuance.**  

The passive cards become a *secondary* feature (exportable audit feed) that can be toggled on/off.

---

## 3. SPoF / surveillance substrate – reconcile or refute

*Yes, a single choke‑point is a SPoF, but we mitigate it with three engineering guarantees:*

1. **High‑availability cluster** (3‑node Raft consensus) – failover < 200 ms.  
2. **Write‑through cache** – every decision is persisted to an append‑only log before returning; replayable for disaster recovery.  
3. **Zero‑trust telemetry** – every request is signed with the caller’s OAuth token; logs are immutable (WORM) and can be streamed to the customer’s SIEM.  

The “surveillance” concern is answered by **data‑ownership**: the logs are **customer‑owned**; we only provide a managed ingestion pipeline. This turns the surveillance objection into a compliance advantage.

---

## 4. Can we mediate writes and still be “incapable of harm”?

We re‑define “incapable of harm” as **“incapable of unintended, nondeterministic harm.”** All enforcement decisions are **pure, auditable, and reversible** (override via a signed admin token). The only possible harm is a *blocked* change, which is **explicitly authorized** by the policy owner. Therefore the claim holds under the new definition.

---

# FORCE A DECISION

### 1. Exact v1 (90‑day) scope – one paragraph

> **TeamCTX v1** is a deterministic Policy Enforcement Plane that sits between source‑control (GitHub/GitLab) and the CI orchestrator (Jenkins/ArgoCD). It consumes real‑time webhook events, materializes an event‑sourced permission graph, and on every push or PR merge request evaluates a PDP rule set (expressed in `.teamctx.yaml`). If a rule is violated (e.g., a PR touches a repo owned by a Jira ticket lacking the `security‑approved` label), the PEP returns a **deny** and issues a signed lease token that the CI system must present to proceed. All decisions are logged to an immutable audit stream that the customer can forward to their SIEM. The product ships with **two connectors**: **GitHub/GitLab** (source‑control) and **Jenkins/ArgoCD** (CI). No other integrations are in scope for the first 90 days.

### 2. First design‑partner profile

- **Company size:** 150‑300 engineers, split across 3–5 product squads.  
- **Industry:** Regulated software (FinTech / HealthTech) where a *policy‑block* on unaudited code changes is a compliance requirement.  
- **Decision‑maker:** VP of Platform Engineering (or Head of DevSecOps) who controls the CI/CD pipeline budget and can sign off on a “security‑gate” purchase.  
- **Why they sign:** They have an existing “security‑approved” label workflow in Jira and are forced by auditors to enforce it before code can be merged.

### 3. North‑star metric

**“Policy‑block conversion rate”** – the percentage of policy violations that result in a *forced* remediation (i.e., a blocked PR that is subsequently relabeled and re‑submitted). A healthy product maintains **≥ 85 %** conversion, proving that the enforcement is both useful and not overly noisy.

### 4. Pricing wedge

- **Free tier:** 1 repository, unlimited reads, **no enforcement** (pure evidence broker).  
- **Pro tier (per‑seat):** $25 / dev / month, includes deterministic enforcement on up to 5 repos and CI integration, with audit log export.  
- **Enterprise gate:** $0.10 / policy‑evaluation call (rounded to the nearest 10 k) plus optional SLA for HA clusters. This aligns revenue with usage (each block/lease is a billable event) and scales with the size of the enforcement surface.

--- 

**Bottom line:** We must abandon the “read‑only” myth, double‑down on deterministic enforcement, and launch the PEP with GitHub/GitLab ↔ CI as the minimal viable choke‑point. The market will fund us only if we can **block** a change and force a compliance step; everything else is secondary.