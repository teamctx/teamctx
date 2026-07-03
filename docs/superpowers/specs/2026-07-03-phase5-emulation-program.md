# Spec: Phase 5 team-emulation validation program

## Status
Revision 2, after an Opus 4.8 adversarial spec review (verdict on rev 1: REVISE-FIRST; two
P0, eight P1, six P2, all accepted and pinned below; the review also verified two things a
runner would otherwise re-litigate: synthetic PreToolUse events ARE faithful to what the
hook consumes, and ONE operator token suffices because the product keys on branch and
timestamp, never author identity). Goal source: Edgar, 2026-07-03: "test it like a team of
people + agents that works with Jira, Confluence, GitHub, and GitLab, and make sure it all
works as expected." RUN-READY after Phase 4 merges and the S8b seam lands.

## What is being proven
Not that the code passes tests (CI proves that), but that a REAL multi-actor team flow
produces the surfacing the product promises, live, on all four sources; every scenario
records expected vs actual as durable evidence; the corpus seeds the Phase 3 numbers.

## Actors (emulated; one operator credential is sufficient BY DESIGN)
- **Actor A "author"**, **Actor B "agent dev"**, **Actor C "reviewer/PM"** as rev 1
  (separate clones, distinct branches; B has the hook + snippet; agentic rows drive an Opus
  subagent; deterministic hook rows drive `teamctx-hook` with synthetic PreToolUse events).
- **Corrected rationale (review P1-1):** collision own-detection keys on the PR/MR HEAD
  BRANCH vs the request branch; criteria keys on TIMESTAMPS (issue `updated` vs the derived
  `since`). Author identity is never consulted, so one token authoring everything stages
  every role; the load-bearing variables a driver must control are BRANCH and ORDER-OF-
  OPERATIONS, not identity.
- **Hook-driver trap (pinned):** the hook is once-per-session via a marker file; every
  driver invocation uses a FRESH `session_id` (or clears `TEAMCTX_HOOK_CACHE`), else the
  second run silently no-ops and reads as an empty actual.

## Lab assets
As rev 1 (private `teamctx-emulation-lab` on GitHub + GitLab; Jira project + Confluence
space on the operator instance once Edgar names them), with pins:
- **Gate staging (P1-4):** the GitHub workflow and GitLab pipeline each include a
  deliberately slow job (`sleep 120`) so the live pending state is reliably observable; the
  canceled-with-zero-failed-jobs recipe is pinned: trigger, then cancel via API before any
  job starts.
- **Write scope (P1-6):** when Edgar names the Jira project + Confluence space, step zero
  is a WRITE-SCOPE verification (create + delete one clearly-labeled test issue/page);
  "a key was named" is not "the token can write". Until then, the Jira/Confluence
  fire-paths run against synthetic state (recorded as exactly that) while their live READ
  sub-checks (space-key typo -> unavailable; unconfigured-Jira KEY-N -> disabled) run now.
- **Drivers live in TEAMCTX (P1-7):** a top-level `emulation/` directory in the teamctx
  repo (excluded from the package), committed and sanitized, so the corpus is regenerable
  after the disposable lab repos are deleted. The lab repos hold only lab content.
- **The S8b seam (P0-1, decided):** `GITHUB_API_ROOT` becomes env-overridable
  (`TEAMCTX_GITHUB_API_ROOT`), landed as a micro-slice right after S8. The unbounded row
  (below) drives a fabricated 301-PR payload from a local mock server through the REAL
  CLI/render/hook and its evidence is tagged `test-verified (fabricated payload, real
  pipeline)`. Live-unbounded (a real 300+-PR repo) remains a named residual, never silent.

## Scenario matrix (revised; each row pins setup ORDER, transport, and expected form)
1. **Collision, GitHub**: as rev 1 + own-PR FYI sub-row.
2. **Collision, GitLab**: MR terminology/web_url/no-gh-hint, PLUS the own-MR FYI sub-row
   (P1-3: the GitLab own-detection is a distinct code path; it gets its own evidence).
3. **Gate, GitHub**: failing check -> firing; the slow job -> live pending; token removed ->
   can't-verify; PLUS (P1-8) the zero-check-runs case reads CLEAR, affirmatively recorded
   as the documented GitHub/GitLab asymmetry.
4. **Gate, GitLab (the P0 scenarios)**: as rev 1, with the pinned cancel recipe;
   zero-pipelines reads the disabled note, never clear (the other half of the asymmetry).
5. **Criteria, GitHub, split (P2-3) with pinned order (P1-2)**: (a) create issue -> B
   branches `42-fix-auth` (fixing `since`) -> C edits the issue AFTER -> fires with detail;
   (b) issue derived but unchanged -> the CLEAR line carries `(issue #42 from your branch
   name)` AND the `since` provenance (`when you branched (merge-base ...)`) is asserted
   templated (P2-6). Issue numbers in expected blocks are TEMPLATED (`#{n}`), byte-exact
   only for stable copy spans (P2-1).
6. **Criteria, Jira**: as rev 1 with the same pinned order; the unconfigured-Jira KEY-N
   disabled note and the mixed-family no-false-clear case are LIVE-runnable read checks
   now; the fire path needs write scope (see Lab assets).
7. **Docs, local**: as rev 1; pinned (P2-4): a clean configured docs tree reads CLEAR
   (fresh; the S5b real green), `not_applicable` appears nowhere.
8. **Docs, Confluence (transport corrected, P0-2)**: the reflex-skip note is asserted on a
   FULL `work-start` run with `profile=reflex` ("Not checked:" carries the skip note); the
   HOOK row asserts docs SILENCE (docs is not a glanceable check) and that nothing the hook
   says disagrees. Openability is recorded as a live-verified boolean, never a committed
   clickable URL (P2-2).
9. **Onboard/status truth**: as rev 1 (status captured and checked true after every
   mutation stage).
10. **Transports agree (P2-5)**: uses a CONFLICT scenario (the hook speaks conflict, so
    agreement is non-vacuous); MCP invoked with `TEAMCTX_PROJECT_ROOT` set to the clone and
    the same paths/branch; shares its composed state with row 11.
11. **Replay (P1-5)**: same composed scenario; the driver replays with the IDENTICAL
    `observed_at` against captured payloads offline (the seam), asserting identical digest
    and identical output. Live sources are never assumed frozen.
12. **Unbounded at scale (new, P0-1)**: fabricated 301-PR payload via the S8b seam ->
    "Partially checked" with n=300, hook copy verbatim, never clear; evidence tagged
    test-verified (fabricated payload, real pipeline).

Degradations with NO seam (real rate limiting) stay unit-verified and are RECORDED as such.

## Evidence, sanitization (P2-2, concrete), orchestration
As rev 1, plus the redaction map, applied by the driver before anything is committed:
the Atlassian base URL -> `https://ATLASSIAN.example`; project key -> `PROJ`; space key ->
`SPACE`; issue/page ids -> `{id}`; the GitHub/GitLab lab repo slugs are committed AS-IS
(they are our disposable lab assets, not instance data). Expected blocks declare per-span:
byte-exact (stable copy) vs templated (`{n}`, `{url}`, `{id}`). A FAIL stops the program
until fixed and re-run.

## Exit bar (sharpened)
Every row PASS live on GitHub + GitLab, including both halves of the gate asymmetry and
both own-PR/own-MR FYIs; Jira + Confluence read sub-checks PASS live now, fire paths PASS
live once write scope is verified (until then: synthetic, recorded as such); row 12 PASS
through the real pipeline via the seam; residuals NAMED with reasons (live-unbounded, real
rate limiting), never silently folded into "it all works." Evidence summary committed;
CURRENT.md updated.
