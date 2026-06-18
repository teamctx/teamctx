# Role-play panel — Claude (independent, pre-convergence)

*Authored without reading the frontier panel outputs, to keep the convergence honest.
Three roles, sharpest objections + honest concessions. Lens: product / adoption /
impact only. The CTO/formal-safety angle is deliberately out of scope (saturated by the
referee panels).*

---

## ROLE 1 — CPO / Head of Product

**The one product bet most likely wrong.** That **structural relevance is enough.** The
measured number is ~38% coverage of high-value events; the product bets that the
*certifiable* 38% (highest-confidence, costliest-to-miss) plus the **L→D flywheel** is
enough to be indispensable. But the flywheel is a **behavior-change bet dressed as an
architecture decision** — it only turns if teams *write tribal knowledge into declared
artifacts*, and teams famously don't. If the flywheel stalls, teamctx is frozen at 38%
and *feels* partial forever. The deepest risk in the whole vision is behavioral, not
technical.

**Painkiller or vitamin?** Diffuse-pain painkiller — which is the worst kind to sell.
Prevented rework and averted collisions are real money, but **nobody has "stale-context
pain" as a named, budgeted line item** today. Solo (Maya) adopts first (zero-config,
free, instant) but feels it as a vitamin. Enterprise *pays* first, for the safety/privacy
*gates*, not the savings. So the product must win **two different beachheads with two
different promises** through one artifact — a focus hazard.

**Indispensable vs. shelfware.** Solo: it must be **invisible and zero-maintenance** —
the first time Maya has to tune a policy or babysit a daemon, she's gone. Enterprise: it
must be **paved-road, on-by-default, provisioned by platform** — adopted at the platform
layer, never dev-by-dev, or it dies in the "yet another tool" graveyard.

**Cut from v1.** The **durable collective-memory layer.** It's a different product with
the hardest trust story (consented collective graph vs. can't-track), and shipping it
alongside the broker **dilutes the crisp "can't-track by construction" headline** with a
"but the durable half *can* track, by consent" asterisk. Ship the stateless broker alone;
prove the read-half's provable guarantees first.

**What makes me champion it.** A **counterfactual receipt**: in a real repo, the agent
ships the right thing *because* of a card it would otherwise have missed — shown beside
the same agent shipping the *wrong* thing without teamctx. Indispensability is proven by
the averted disaster, never by the token graph.

---

## ROLE 2 — Head of Engineering / Platform (has to run the daemon)

**The operational objection that matters most.** *"You want an always-on daemon holding
per-dev OAuth for every source system, fanning out on a refresh loop, in front of every
agent session — and the payoff is prevented rework I can't measure."* The ops cost is
**concrete and daily**; the benefit is **diffuse and counterfactual.** Nadia's persona
answers the *failure-mode* fear (fail-safe, degrade-to-stale) but not the *why-run-it-at-
all* fear when ROI is unmeasurable. And the **token/credential custody**: a central
read-only store of every dev's metadata access across all systems is still a serious
**exfil target** — "read-only" caps write-harm, not breach value.

**Route-around / surveilled — real or managed?** Surveillance is genuinely *managed*
(artifact-centric, no people-graph — the strongest part of the story). **Route-around is
real and under-addressed**: the surface is *voluntary-attention-based* (prints, never
blocks), so a single noisy/wrong/slow moment and devs stop reading — and a teamctx that's
"on" but unread is **strictly worse** than not deploying (ops cost, zero benefit).

**The single failure that ends trust.** A **certified card that's wrong** — a "collision"
that wasn't, served from a stale cache stamped fresh, or surfaced past an ACL skew. The
certified|hint firewall's entire value ("rely without checking") collapses on the *first*
certified-but-wrong card. The design knows this (trust is multiplicative) — but the **A5
ACL-skew and A3 unsigned-metadata residuals are exactly where a "certified" card can be
wrong**, and they're load-bearing and unproven in the field.

**Why a pilot stalls after week 2.** The cards are mostly **things devs already knew**
(their own open PRs). The novelty gate helps, but if the *novel-save* rate is low, the
daemon becomes wallpaper — week-1 novelty wears off, week-2 it's background noise nobody
glances at. **Rare saves don't build a habit.**

---

## ROLE 3 — Exec sponsor (impact lens; not revenue)

**Impact thesis, one line.** *"teamctx lets us safely turn agents loose across all our
source systems without them shipping against stale team state or becoming an injection
vector — the thing currently gating agent adoption at scale."* It clears the sponsor bar
**only if that gate is felt today.**

**The blind spot that kills exec support: timing.** If our agent adoption is still
pilots-not-paved-road, the cross-team-collision-at-scale pain isn't felt yet — we'd be
sponsoring a fix for a problem we don't have *yet* (teamctx 18 months early). If it's
late, the **agent vendors ship native context/memory that's "good enough"** and
commoditize the wedge. The bet is the *window* where teamctx is both needed and
un-commoditized — and nobody has sized that window.

**Is "safety boundary against prompt-injection supply chains" the banner?** **No — lead
with the averted-incident story instead.** Leading with injection-supply-chain is a
**fear sell of an abstract threat**: it sells to security (low budget/initiative vs. the
platform org) and risks sounding like FUD for a threat most orgs don't feel concretely
today. The *differentiated* promise (can't-track / bounded-harm by construction) is the
abstract one; the *concrete* promise (rework/incidents averted) is the commoditizable
one. Lead with **concrete-and-trust-flavored** (the averted incident), not the abstract
supply-chain banner.

---

## OUT of character — the one thing the vision is NOT seeing

**Distribution / the moment-of-invocation.** The entire vision describes what teamctx
*does* once an agent calls `get_context` at work-start. It says almost nothing about
**how agents reliably come to call it** — across Claude Code, Codex, Cursor, Gemini — at
the right moment, *by default*, without the user wiring it up. "Output is just data, every
agent reads it" is true but **passive**: it assumes the integration exists and fires. The
unglamorous, make-or-break problem is the **integration surface** — getting it invoked by
default in every agent's work-start path. The product is architected for **trust**; it is
not yet architected for **distribution** — and distribution is what decides whether the
certifiable 38% ever reaches a single developer. (This is also the deeper reason to cut
the durable layer for v1: spend the focus on getting *invoked*, not on a second product.)
