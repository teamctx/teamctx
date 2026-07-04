# The ambient plan: make teamctx appear as magic

**Product direction, set by the CPO 2026-07-04, verbatim intent:** users NEVER run commands.
Ambient team context. It should just work and appear as magical to the user, or nobody will
use it. This plan is the CTO's translation of that frame into workstreams. Status: proposed;
adversarial spec review before any build, like every arc.

## The bar, stated as an experience
A developer (or their agent) installs once and sets up once. From that moment on, the right
team context simply appears: at the moment work starts, and again the moment something
relevant CHANGES, saying only what changes a decision, and never asking to be invoked,
configured per-use, or remembered. A teammate who clones the repo gets the same experience
with at most one step. Everything already proven about honesty (a green means checked; gaps
say so plainly) holds unchanged; ambient must never mean noisy, and never means stale-clear.

## Where today's product already meets the bar
One-time `teamctx onboard`; the Claude Code hook fires by itself before the session's first
edit (one network round-trip, never blocks); agents get the same answer over MCP; the
committed config makes the setup shareable. The gap is everything after that first moment,
every actor outside Claude Code, and the teammate's first five minutes.

## Workstream A: ambient MOMENTS (the core of the magic)
Today context appears once per session. Magic is appearing exactly when reality changes.
- **Delta-aware re-grounding.** Cache the last answer's replay digest per session and input
  set (local `.teamctx/` state, never committed). Re-check quietly on cheap triggers; SPEAK
  only when the answer differs, and say the difference ("since you started: PR #7 appeared,
  touching this file"), not the whole report again. The contracts already reserve the
  `changed_since_start` signal type; this workstream finally earns it. Silence discipline is
  a feature: one utterance per change, digest-deduped, never a repeat.
- **More first-moments.** Ground on the session's first user prompt (UserPromptSubmit hook),
  not just the first edit, and on branch switch (the working tree's branch changing between
  checks is itself a cheap trigger). Both reuse the existing one-round-trip reflex budget.
- **Honest staleness window.** Between checks the answer can age; the delta model makes the
  window explicit and short instead of session-long.

## Workstream B: ambient for EVERY actor
- **Teammates, zero-step.** onboard gains a team mode that commits the project-scoped hook
  entry (`.claude/settings.json`) alongside the config, with a graceful no-op when teamctx
  is not installed (a committed hook must never break a non-user). A teammate who clones the
  repo and has teamctx installed gets ambient context with zero steps; one documented
  install step otherwise.
- **One-liner install.** pipx/uvx-able packaging so the single setup step is trivial. This
  makes the parked **PyPI publish an Edgar call that now gates the magic bar**, flagged, not
  assumed.
- **Agent runtimes beyond Claude Code.** The MCP tool is pull today; ship per-runtime
  ambient recipes (the snippet convention now, harness-level auto-invocation where each
  runtime supports it) so an agent never has to decide to ask.

## Workstream C: magic-grade feel
- **Latency.** Sub-second repeat grounding via conditional requests and the local cache;
  the first check stays one round-trip; measure and pin budgets in tests.
- **Utterance quality.** The M2 voice already speaks plainly; the delta model sharpens WHAT
  is worth saying. The polish backlog rides along (the missing-period join; "this branch
  isn't on GitHub yet" copy).

## Workstream D: every surface obeys the ambient law (copy)
The landing page is done (merged `93f450b`). Remaining, small and immediate: the README
story pass (setup ends the command story; work-start appears only as the way to reproduce
the samples); the CLAUDE.md snippet rewritten around receiving context rather than running a
command (with the run-it instruction kept only as the fallback for environments without the
hook); onboard's next-step line ("edit any file in a Claude Code session and the context
appears" instead of "run work-start"). The ambient-law memory is recorded so no future
surface regresses to command-first framing.

## Workstream E: prove the magic (the evidence bar, extended)
New emulation rows: a mid-session change APPEARS without any invocation (the delta row); the
teammate-clone zero-step row; silence rows (no repeat utterance on an unchanged answer); a
latency-budget row. Same discipline as the twelve: expected blocks from the real pipeline,
committed evidence, named residuals only.

## Sequencing (each slice complete to the bar; reviews as always)
D (copy, immediate) -> A (delta-aware re-grounding + new first-moments; the engineering
heart) -> B (zero-step teammates + packaging + runtime recipes; PyPI call sits here) ->
C (latency pinning) -> E (evidence rows) -> refresh all claims.

## The one call reserved for Edgar
PyPI publish (it now gates the one-liner install that the magic bar wants). Everything else
proceeds under the standing operating model.
