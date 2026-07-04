# The ambient plan: make teamctx appear as magic

**Product direction, set by the CPO 2026-07-04, verbatim intent:** users NEVER run commands.
Ambient team context. It should just work and appear as magical to the user, or nobody will
use it. **Revision 2**, after an Opus 4.8 adversarial review of rev 1 (verdict REVISE-FIRST:
four design-level P0s, five P1s, three P2s, all accepted and pinned below). Workstream A
must not build before its pins hold; the committed-hook idea from rev 1 is REJECTED with its
reason recorded.

## The bar, stated as an experience
Unchanged from rev 1: install once, set up once, then the right context appears at the
moment work starts and again when something relevant changes, saying only what changes a
decision. The honesty laws hold; ambient never means noisy, and never means stale-clear,
INCLUDING stale-clear by cached silence (P0-2 below).

## Workstream A: ambient moments (pins are law)

**A1. The content-identity digest (P0-1).** The replay digest hashes volatile time fields
(`requested_at`, signal `created_at`/`observed_at`/`expires_at`, status `last_checked_at`,
`request_id`) and therefore differs on every run by construction; it is the WRONG identity
for delta comparison and stays untouched as the replay artifact. A new pure-core
`content_digest` covers exactly: signal (type, source_family, scope, evidence_summary,
source_display, freshness, confidence, visibility), status (source_id, family, status,
safe_user_message, visibility), and the derived closure statuses; it excludes every volatile
field above. Tests: mutating each decision-bearing field changes it; mutating each volatile
field does not.

**A2. The silence law (P0-2).** Silence is a claim: "nothing changed since a known-good
check at {time X}", and it must always carry that X internally. A baseline is VALID for
future silence only when its important checks were positively checked (clear or an
already-surfaced finding) and coverage did not shrink. An answer containing an unreachable,
pending, or unbounded important check is NEVER a valid baseline: every subsequent moment
must either re-surface the gap or state the delta ("still couldn't check open PRs"). A
re-check failure never downgrades a prior good baseline into silence; it speaks.

**A3. The marker is superseded (P0-3).** The once-per-session marker's job (cost bound +
no retry storms) transfers to the delta cache, which becomes the ONE owner of hook state
(the `/tmp` marker dies; no split-brain between two cache homes). Cost bound: a pinned
minimum interval between network re-checks per cache key (default 90s), enforced in the
cache; within the interval the hook is silent-by-interval, which is only legal under A2
(a non-good baseline forces the gap to re-surface regardless of interval). Failure path:
re-check errors leave the baseline untouched and stay quiet ONLY if the baseline was good;
otherwise the gap speaks.

**A4. Trigger reality (P1-1).** Verified against the Claude Code hooks docs: there is no
branch-switch event, and UserPromptSubmit carries no tool_name/file_path. Pins: (1)
UserPromptSubmit grounding is coverage-limited by design (dirty-tree paths only; on a clean
tree it grounds gate/criteria/docs and says nothing about collisions unless one exists) and
uses its own `hookEventName: "UserPromptSubmit"` emit; (2) branch switch is a DERIVED
invalidation, not a trigger: branch lives in the cache key, so any real trigger after a
switch misses the baseline and re-grounds; (3) a verification step pins the minimum Claude
Code version and confirms the event set in the target version before build; no experimental
events are assumed.

**A5. The delta signal through the one seam (P1-2).** `changed_since_start` is minted at
the impure edge that owns the cache (never in the pure core), enters the composed documents
as a normal signal, and is classified by `assess()` and spoken by the shared render and the
hook with new voice-ruled copy (a delta on an important check is a heads_up; CLI, MCP, and
hook may differ in length but never in facts). It does not bypass the M2 single-
classification seam.

**A6. Dedup rule (P2-3).** Last-value comparison, explicitly: a PR closed and then reopened
returns the content digest to a prior value and SPEAKS again (a seen-set would wrongly
suppress a genuine re-appearance). One utterance per change of current state.

**A7. Cache key and hygiene (P1-4).** The key enumerates: resolved repo + forge + branch +
normalized path set + issues + since + docs_root + profile + token-presence + a config
content hash + the teamctx version. A superset path set is a new baseline, never a match.
Contents: the content digest and minimal delta material only; never tokens, never raw
evidence text beyond what the delta must restate; file mode 0600; lives under `.teamctx/`
with a name the trackable-stanza keeps ignored; per-(session, repo, branch) so multi-repo
and linked-worktree sessions never cross baselines (P2-2; the worktree cache path gets an
explicit test).

**A8. Cold start (P2-1).** The first ambient moment with no credential IS the setup
surface: the hook's can't-verify copy already names the one env var to set; the plan makes
that the designed first-run experience, never a silent non-start.

## Workstream B: every actor, consent-first (P0-4 resolved by design change)

**The rev-1 committed-hook idea is REJECTED.** Committing an auto-run command to
`.claude/settings.json` is a documented supply-chain pattern (config-file trust
laundering); the graceful no-op either surfaces errors to non-users or requires committing
an executable, worse; and the zero-step claim cannot be proven by the offline harness
(Claude Code's auto-fire is not teamctx behavior). Recorded so it is not re-proposed.

Pinned design instead:
- **Committed: config only** (`.teamctx/config.json`, inert data, already the shareable
  seam).
- **The reflex is a per-actor, knowing opt-in** and moves to `.claude/settings.local.json`
  (gitignored). TODAY's onboard writes the hook into the committable `.claude/settings.json`;
  that latent leak is fixed as its own small slice (B1) with migration for existing installs
  and README/onboard copy updated to say where the hook lives and why.
- **The teammate story is one documented step**: install + `teamctx onboard` (which they
  run and see). The magic claim for teammates is "one command, then ambient", stated
  exactly so.
- PyPI publish (Edgar's call) gates the one-liner install; per-runtime ambient recipes for
  non-Claude-Code agents ride the snippet + MCP as before.

## Workstream C: feel, with honest mechanics (P1-3)
"Sub-second" means the cache-served path (no network), which exists only under the A2
silence law and carries its "since X". Re-checks cost a real round-trip and are bounded by
the A3 interval; GitHub GraphQL (the collision path) has NO conditional-request support, so
ETags are dropped as a latency mechanism; If-None-Match on the REST checks/issues probes is
a rate-budget and payload saving only, claimed as exactly that. Latency is measured live or
with injected RTT, never from a localhost mock.

## Workstream D: the copy law on every surface
As rev 1; the first slice (snippet receives, next-steps promise appearance, README story
ends at setup) is built and in review as of this revision.

## Workstream E: prove the magic (P1-5)
The harness gains a DELTA MODE: same session id, persistent cache dir, mock state mutated
between invocations. Rows assert: unchanged second run emits nothing AND the silence is
attributable to delta-dedup, not a leftover marker; changed second run speaks exactly the
delta; an unreachable second run re-surfaces the gap (the A2 row); the reopened-PR case
re-speaks (A6). The latency row is live or injected-RTT and labeled accordingly. The
teammate row proves the one-command story offline (onboard in a fresh clone) and labels the
Claude-Code-auto-fire portion a live/manual residual, never "proven offline".

## Sequencing (unchanged shape, gated)
D (in review) -> B1 (the settings.local.json fix, small and standalone) -> A (only after
its pins are encoded in the slice spec) -> B (teammate story + packaging; PyPI call sits
here) -> C -> E -> refresh all claims.

## The one call reserved for Edgar
PyPI publish. Everything else proceeds under the standing operating model.
