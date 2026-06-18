# teamctx — Personas & Journeys

*Companion to [day-in-the-life.md](day-in-the-life.md) (solo founder Maya; enterprise IC Devi). Here: the eng lead, the PM/business author, and the security/platform admin. Each grounded in the [protocol](../../research/teamctx-protocol-v0.3.md), with the win, the fear it must clear, and the honest limit.*

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

## Persona coverage (at a glance)

| Persona | Primary win | Fear it must clear | Honest limit |
|---|---|---|---|
| Maya — solo founder | Agent knows her own work, cross-agent, zero-config | "another thing to manage" | local-only relevance; no team graph |
| Devi — enterprise IC | Collisions/stale-spec/missed-gate averted at work-start | noise / wrong cards | relevance ceiling; fidelity ≠ truth |
| Raj — eng lead | Less rework + review load; tunable noise floor | surveillance revolt | won't catch unwritten knowledge; no enforcement (by default) |
| Priya — PM/business | Her decisions actually reach the work | being observed | only typed/linked artifacts propagate |
| Sol — security/platform | Can *approve* agents on internal systems | injection/exfil/surveillance/SPOF | trusts ACL mirroring + unsigned metadata; agent cooperation |

**The consumer (the agent itself)** is the sixth stakeholder: it gets compact, typed, permission-scoped evidence with explicit `Unknown`, in a format any model reads — so it stops re-deriving team state and stops mistaking absence for clearance.
