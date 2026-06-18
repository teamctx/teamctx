# teamctx — Personas & Journeys

*Companion to [day-in-the-life.md](day-in-the-life.md) (solo founder Maya; enterprise IC Devi). Here: the eng lead, the PM/business author, the security/platform admin, the principal engineer (technical authority), and the SRE who operates the daemon. Each grounded in the [protocol](../../research/teamctx-protocol-v1.0.md) and the [architecture decision record](architecture-decision.md), with the win, the fear it must clear, and the honest limit.*

---

## Persona 3 — Raj, Engineering Lead (8-person squad)

**Pain.** His squad runs agents. He fears agents shipping against stale context (the collision, the rounding bug) → review burden and incidents. He *equally* fears a tool his team experiences as productivity surveillance — they'd route around it.

**How he's served.** Raj rarely reads cards himself; he owns the team's `.teamctx` **relevance policy** — deterministic blast-radius rules (`touching payments/ → require linked finance issue`) and severity thresholds that set the noise floor. Over weeks he sees fewer *"the agent did the wrong thing"* PRs in review. After an incident, he replays exactly what context the agent had.

**Win.** Lower rework + review load; agents that respect the team's real constraints; a **configurable, deterministic noise floor** (no ML) so it never becomes alert spam.

**Fear cleared.** Artifact-centric + can't-track → the team doesn't feel monitored. It's a Navigator, not a cop: no blocking by default.

**Honest limit.** The relevance ceiling — it won't catch tribal knowledge that isn't written down. And it won't *enforce*; if Raj wants a hard "block on unreviewed `auth/`," that's an explicit opt-in config whose availability-harm trade he owns.

*Grounded in:* programmable relevance (§6), policy-as-code, replayable audit, no people-graph.

---

## Persona 4 — Priya, PM / Product Owner (lives in Jira + Confluence)

*The subtle one: does the business author feel served, or just observed?*

**Pain.** *"I update acceptance criteria and the rounding policy, and engineers — now their agents — build the old thing anyway. My decisions don't reach the work."* Her systems of record feel like where decisions go to die.

**How she's served.** She installs nothing and changes nothing. She keeps working in Jira/Confluence. teamctx turns her authored artifacts into the cards that reach Devi's agent **at the moment of work** (`acceptance_criteria_changed`, `doc_superseded`). Her decisions finally *land* — automatically, at the right time, in front of the right task.

**Win.** Her authority *propagates.* The thing she wrote actually changes what gets built. teamctx is the **distribution layer for her decisions** — without her chasing anyone.

**Fear cleared (served, not surveilled).** teamctx amplifies her *artifacts*, not her *behavior.* It cannot and does not record *"Priya keeps changing the spec"* — there is no people-graph. It surfaces the criteria, not the author's patterns. The devs aren't surveilled either; the relationship is symmetric.

**Honest limit (and a healthy nudge).** teamctx only carries what she puts in **typed/linked artifacts.** A decision buried in a Slack DM won't propagate (no DM ingestion — a hard invariant). This *nudges* her to write decisions into the systems of record — a feature, but also a limit: it can't save a team that doesn't write things down. And **fidelity ≠ truth**: if her criteria are wrong, teamctx faithfully propagates wrong criteria. It distributes decisions; it doesn't grade them.

*Grounded in:* tracker/docs connectors → `acceptance_criteria_changed` / `linked_doc_changed`; artifact-centric (can't-track); A1 (only typed/linked artifacts propagate).

---

## Persona 5 — Sol, Security / Platform Admin (onboarding & governance)

**Pain.** *"Engineering wants agents reading our GitHub/Jira/Confluence. That's something touching everything — injection, exfil, and surveillance risk in one. My default is no."*

**How he's served (the onboarding journey).** He evaluates and finds, provably:
- **Read-only** — no write path, so it can't act on or break prod (fail-safe if down: agents lose context, they aren't blocked).
- **Per-dev impersonated OAuth, least-privilege metadata scopes** — no god-mode service account.
- **Deterministic + replayable** — he can audit exactly what any agent saw, and re-derive it.
- **Artifact-centric audit** — passes works-council/privacy review because it logs *eligibility of artifacts*, not *developer behavior.*
- **Typed evidence channel + malicious-input corpus** — injection-resistant *selection.*
- He sets the **declassification dial** (`δ=none`) so cross-permission existence never leaks.

**Win.** He can say **yes** to agents on internal systems *because* the boundary is provable and auditable. The usually-unapprovable (a context layer touching everything) becomes approvable *precisely because* it's deterministic, read-only, and can't-track.

**Fear cleared.** SPOF/availability — read-only + no enforcement by default means downtime degrades gracefully. Surveillance — artifact-centric, no people-graph.

**Honest limit.** He must trust connector **permission mirroring** (A5 ACL skew) and **unsigned metadata** where sources can't sign (A3); and end-to-end injection safety still needs the agent to cooperate (teamctx hardens its pipe, not the model).

*Grounded in:* read-only; T2′ existence-privacy + δ dial; signed κ replay (audit); T3′ feature-mediated selection; A3/A5 residuals.

---

## Persona 6 — Wei, Principal Engineer (technical authority across ~6 squads)

*The leverage persona — his value is judgment that scales past his own keyboard, or doesn't.*

**Pain.** *"I make the call — money math is decimal, no new service without an ADR — and weeks later three squads have drifted and an agent has confidently shipped the worse pattern. I find out in review, every time."* Two failures that feel identical from his chair: his decision never reaches the agent (buried, or not trusted enough to act on), **or** it reaches them and a fluent generation overrides it anyway. Either way his judgment didn't govern the work, and his leverage stays capped at his own keyboard.

**How he's served.** He declares the mandate **once** — a broad-scope authority declaration (lightweight in `.teamctx`, or governed in the durable layer): *scope → source → priority*. teamctx turns it into a **certified, high-severity authority card** that reaches every squad's agent at work-start, with provenance («per ADR-12»), agreement suppressed and dissent demoted-never-hidden so it isn't drowned. He's the persona that most drives the **L→D flywheel**: the standard "everyone knows" that lives in no ticket is exactly what teamctx's honest `Unknown` nudges him to *write down*, so it becomes governable instead of re-derived.

**Win.** His judgment governs the work without him in the loop. And the part that serves the ego *honestly*: an agent shipping against his mandate is now a **visible, replayable** event, not a silent one — replay proves the authority card *was present*, so it's "the agent knowingly overrode a declared authority," never "nobody told it." That's what lets him **stop reviewing every PR** — a missed mandate is no longer invisible.

**Fear cleared.** He gets reach **without** surveillance (no people-graph — it amplifies his *artifact*, not anyone's behavior) and **without** becoming a blocking gate (informational, never enforced). A broad mandate that hard-blocked would just get teams routing around the whole system — the surveillance-revolt failure at architecture scale; *printing, not blocking* is what keeps his authority adopted.

**Honest limit.** teamctx makes an override **visible, not impossible.** It closes the *ignorance* path; it cannot stop a non-cooperating model from generating against the card — that's a CI gate's job, deliberately a different tool, and the same residual Sol carries (teamctx hardens its pipe, not the model). And **fidelity ≠ truth at the authority layer**: it faithfully propagates a *stale* mandate, so a broadcast decision is only as good as its upkeep (the ossification risk — a mechanically re-asserted bad call is worse than a forgotten one). When his broad mandate genuinely collides with a squad's local reality, teamctx surfaces a **conflict card** (refuse-to-pick); it does not ram the mandate through.

*Grounded in:* authority as a first-class declared record (D6 — resolved/missing/**conflicted**/temporary; informational, never enforced; suppress-agreement/demote-dissent); broad-scope declaration (`.teamctx`→durable, additive-with-investment); the L→D flywheel (D7); signed-κ replay (audit); fidelity ≠ truth; bounded-harm honestly scoped (override visible, not impossible — cooperating-consumer residual).

---

## Persona 7 — Nadia, SRE (owns the teamctx daemon in production)

*Sol decides whether to allow teamctx; Nadia is the one who has to keep it alive at 2am. The approve/operate pair.*

**Pain.** *"You're handing me a new always-on service that sits in front of every agent's work-start and fans out to GitHub, Jira, Confluence, GitLab on a refresh loop. So — what's my blast radius, what's my on-call story, and what happens when Jira is degraded?"* Her default fear is a context broker becoming a new SPOF in the critical path and a new pager source.

**How she's served (the operability journey).**
- **Fail-safe by construction** — read-only, and *not* in the write/deploy path. If the daemon is down, agents **lose context, they are not blocked** — degradation is graceful, not an outage. The thing in the critical path of *shipping* is untouched.
- **Known blast radius** — egress is bounded by the **connector allowlist** (the load-bearing rung of the capability ladder); the daemon can only reach declared sources, so "what can it touch" is an auditable list, not a question.
- **Back-pressure, not cascade** — the warm daemon serves from **freshness-stamped per-source caches** refreshed by a background loop with back-off. A slow or down source degrades to **honest staleness** (the certificate reports the freshness bound) instead of blocking requests or hammering the source. Her failure mode is *stale* — visible and bounded — not *hung*.
- **Observable + replayable** — per-source refresh health, cache age, and request latency are the metrics she runs it on; every served context set is replayable for incident forensics.

**Win.** A service she can actually run on-call: the worst common failure is "agents got slightly stale context," self-reported in the certificate — not "agents are down" or "we DDoSed our own Jira." The honesty invariants double as **operability guarantees** — read-only is also fail-safe; the freshness stamp is also her SLI.

**Fear cleared.** SPOF/availability — read-only + degrade-to-stale makes the daemon *removable* from the critical path of shipping. It's a cache in front of read APIs, not a gate.

**Honest limit.** It is still a **real service with real ops surface** — a daemon, caches, and a refresh loop she now owns. **Freshness becomes an SLO**: the certificate's staleness bound is only as good as the refresh loop's health, so a silently wedged refresher becomes confidently-stale cards (caught via refresh-age monitoring, but it's a new failure mode she owns). And refresh-storm back-pressure on rate-limited sources is a real tuning problem, not a solved one.

*Grounded in:* the warm-daemon + freshness-stamped cache (§9; "stateless = no durable *trusted* state, not no cache"); read-only fail-safe (degrade-to-no-context, never block); egress + connector-allowlist rung (D1 capability ladder); freshness → certificate staleness bound; signed-κ replay (forensics). **Pairs with Sol** (approve ↔ operate).

---

## Persona coverage (at a glance)

| Persona | Primary win | Fear it must clear | Honest limit |
|---|---|---|---|
| Maya — solo founder | Agent knows her own work, cross-agent, zero-config | "another thing to manage" | local-only relevance; no team graph |
| Devi — enterprise IC | Collisions/stale-spec/missed-gate averted at work-start | noise / wrong cards | relevance ceiling; fidelity ≠ truth |
| Raj — eng lead | Less rework + review load; tunable noise floor | surveillance revolt | won't catch unwritten knowledge; no enforcement (by default) |
| Priya — PM/business | Her decisions actually reach the work | being observed | only typed/linked artifacts propagate |
| Sol — security/platform | Can *approve* agents on internal systems | injection/exfil/surveillance/SPOF | trusts ACL mirroring + unsigned metadata; agent cooperation |
| Wei — principal engineer | His judgment governs the work; overrides become visible/replayable | being silently overridden (ignored or nullified) | override made visible, not impossible; stale-mandate ossification |
| Nadia — SRE | A broker she can run on-call: worst case is stale, not down | new SPOF + pager source in the critical path | real ops surface; freshness is now an SLO |

**The consumer (the agent itself)** is the eighth stakeholder: it gets compact, typed, permission-scoped evidence with explicit `Unknown`, in a format any model reads — so it stops re-deriving team state and stops mistaking absence for clearance.
