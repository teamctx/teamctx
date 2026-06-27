# Reality-grounding — strategy & north star (2026-06)

**Date:** 2026-06-27 · **Status:** strategy-pass output (CTO/CPO) · companion to
[competitive analysis](../../research/competitive-context-engines-2026-06.md)

## The one-line thesis

teamctx is **reality-grounding for agentic work**: it keeps every actor — agent or human —
pinned to the current, **source-backed** state of the systems a team already lives in. Its
defining property is **no LLM in the content path** — it normalizes, routes, selects, and renders
the record, but it never reinterprets what the record *means*. It transforms the **delivery, not
the content**, so facts arrive verbatim, source-backed, and verifiable. Every other tool in the
agent stack synthesizes, summarizes, resolves, or remembers a lossy version of the record; teamctx
is the one layer that doesn't put a model between you and the source — because the instant a model
interprets in the middle, the thing meant to anchor the system can drift too. Scoped precisely: it
is the reference for *what is currently true in the record* — **not** *what's the right call* (the
agent's job), and **not** *is the record correct* (**fidelity ≠ truth**).

## Why this is the product needed now

- **Everyone's building agents; nobody's building the floor.** The gold rush is on the actors.
  The layer that keeps a growing fleet of agents + humans pinned to one shared reality — so they
  don't each drift into their own confabulated picture — is unbuilt, and gets *more* necessary as
  fleets grow. We're laying the hardwood floor for agent-involved workflows while everyone else
  builds furniture and floats it in space.
- **Foundations are laid first, or not at all.** Drift compounds: one agent's distorted action
  becomes the next agent's reality, so errors propagate and entangle. Grounding early prevents
  the compounding cheaply; grounding late is forensics on a system nobody can reconstruct. Chaos
  is a reasonable risk when everything floats untethered to base reality — and chaos is very hard
  to unravel after the fact. The window to lay a floor closes once the room fills with furniture.
- **The need is orthogonal to model quality.** Faithfulness is not intelligence. A smarter model
  doesn't turn a paraphrase back into the original, can't be proven or audited after the fact, and
  "right on average" is worthless for the slice where being wrong is expensive. The need for a
  deterministic, source-backed layer (no model in the content path) doesn't shrink as models
  improve. This is a floor, not a feature that gets obsoleted.

*Lineage:* the founding thesis of Jurati → Ambara → teamctx, clarified — "here's reality, right
now; decide on that; we promise it's accurate as best we can (nothing is 100%)." Same underlying
primitive as **NetBallast v3** (reality-drift control for networks). **Separate products, one
thesis** — the unification is a north-star lens, never a build directive (merging them would be
the drift trap itself).

## The buyer / wedge

The **in-the-loop developer working through an agent terminal** (Claude Code, Cursor, …) — the
human who delegates to an agent but stays in command (Edgar is user 0). The same engine serves
semi-/fully-autonomous agents directly, at higher stakes (no human to catch a false green).
Market is wide (everyone doing agentic coding); the sharp persona is the craftsperson who wants
to stay the judge of what the agent does.

## The value, stated plainly

- **Wrong info delivered through a terminal you trust is worse than no info.** Nobody cares that
  the agent saved tokens crawling for context if the context is wrong.
- We **don't interpret reality for you; we keep everyone synced to it**, the same way every time.
- A **green means checked, not guessed.**

## Where we win (in-the-loop developer)

- A confident-wrong synthesized answer is worse than honest evidence when you're the one
  accountable — we surface the conflict and let you judge instead of silently picking a winner.
- Honest-UNKNOWN *is* the assurance: we tell you where **not** to trust the green.
- Proactive at work-start beats pull/Q&A — we surface the collision / moved spec / failing gate
  before you think to ask.
- Deterministic = ritualizable: same inputs, same verdict, so "run it before you touch files"
  can become a reliable habit.

## Where we honestly don't (and shouldn't try to)

- **Breadth on the fuzzy, unstructured slice** — synthesizers answer ad-hoc / "why" questions
  across Slack/docs; we certify only the structurally-knowable slice (PRs, gates, declared docs,
  issue state). For fuzzy Q&A they're more useful.
- **Live enterprise integration breadth** (Jira/Confluence/Slack now) vs. our GitHub +
  declared-docs.
- **The ceiling is the position, not a weakness.** No-fuzzy-slice is deliberate: own the part you
  can trust, in a stack where everything else is a guess. Chasing the fuzzy slice is how we'd
  become a worse synthesizer and lose the only thing worth using us for.

## Product moves — turn the moat into something *felt* (ranked)

- **M1 — work_start as a reflex, not a thing you remember (keystone).** Auto-fire at the moment
  work begins (opt-in agent hook / one-line `CLAUDE.md`). Assurance you don't run is worthless —
  and this is also how the grounding *norm* gets planted while habits are still plastic. → fold
  into **Sprint 2**.
- **M2 — actionable honest-UNKNOWN.** Each UNKNOWN names *why* + the one action to close it;
  machine-legible so an agent can self-heal its own coverage. → near-term (**Sprint 2** candidate).
- **M3 — judgeable conflict cards.** Surface-don't-adjudicate done so a human adjudicates in ~10s
  (what changed, the evidence, open-the-source). → already **Sprint 2** (`why`/`open-source`
  rebuild on the broker).
- **M4 — the honest-coverage bar now; the guarantee proven later.** State the bar we can stand
  behind today: *a green never means unobserved sources were okay; UNKNOWN stays UNKNOWN — coverage
  gaps are never folded into a clear.* The stronger "never a false green" *guarantee* is a claim
  that must not outrun its proof, so it waits for the E4/E5 numbers. Still the one claim a
  synthesizer structurally cannot make; matters most in the autonomous case. → design bar = now;
  measured guarantee = **Sprint 3**.
- **M5 — verifiable replay as a trust artifact (expansion).** "This verdict is reproducible;
  here's the digest" — for the accountable / audit-adjacent buyer. Engine already has the replay
  (T1); productize later. → **later**.

## Positioning lead (Sprint 2 README / landing opens with this)

> Before you or your agent touch files, teamctx tells you what changed, what conflicts, what
> failed, and what it couldn't verify — the colliding PR, the moved acceptance criterion, the
> failing gate, the superseded doc — as evidence you can judge, not a verdict it picked for you.
> Why trust it? There's no LLM in the content path: it hands you the record verbatim and
> source-backed, the same way every time, and it says plainly where it couldn't look — UNKNOWN
> stays UNKNOWN. The other tools run all of that through a model and hand back one confident,
> synthesized answer — and a confident wrong answer, delivered through a terminal you trust, is
> worse than no answer at all. A green means checked, not guessed. It's the layer you run when
> being wrong is expensive.

*(Lead with the felt benefit; the no-LLM/deterministic construction is the credibility engine —
the* because*, not the headline. See [positioning.md](./positioning.md).)*

## The surfaced-text principle (the product's voice)

Every string teamctx surfaces — cards, verdicts, coverage gaps, errors — is read by a **human about
to make a decision** (directly, or relayed through their agent). So all of it is **plain** (no
internal jargon — "ground," "broker," a bare "UNKNOWN"), **decision-enabling** (what it means for
what they do next), and for anything that couldn't run, it gives the **reason, how to turn it on,
and what to do if they won't or can't**. Honest, guiding, useful. This isn't polish: our edge is
"evidence the human can *judge*," and a human can only judge a message they can act on — the copy is
*how* the value lands. Reserve "reality-grounding," "attest," "broker" for internal/strategy use,
never for the user. **M2** brings the shared render up to this bar; every user-facing surface
inherits it.

## Risks (honest)

- **Runway vs. the wave.** Early-foundation's real risk isn't wrong direction — it's surviving
  until the agentic-org world arrives. **The wedge is the hedge:** work-start pays off *today*
  with in-the-loop devs. Keep the wedge sacred.
- **Platform mountain.** "Source of truth for the org's agentic OS" requires everyone to route
  through us — a decade-long, trust-and-integration climb. Right summit; not a near-term identity.
- **Moat = ceiling.** We win the buyers who feel the drift pain; we don't win everyone, and
  shouldn't try.
- **GIGO / source-record quality (the caveat our central word demands).** "Reality" here means the
  *record*, faithfully — so a stale or wrong source is propagated faithfully unless freshness,
  authority, or coverage signals catch it. Faithfulness is the promise; source correctness is not
  (*fidelity ≠ truth*). The hedge is the freshness/authority/coverage machinery plus honest-UNKNOWN
  — and saying plainly that we never claim to make the record *true*, only to deliver it undistorted.

## Discipline

North star guides; it does **not** pull anything forward. **Next build = Sprint 2**
(ready-for-others + the M1 reflex), led with the positioning above. The grand vision is what the
wedge grows into — not a thing we build directly.
