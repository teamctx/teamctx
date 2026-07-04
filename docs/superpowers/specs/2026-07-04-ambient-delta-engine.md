# Spec: the ambient delta engine (Workstream A)

## Status
Revision 1, proposed by the CTO 2026-07-04 against the ambient plan REVISION 2 pins (A1-A8,
binding); adversarial review before build. Edgar approved the plan arc 2026-07-04. One
DELIBERATE refinement of pin A2 is flagged in section 3 for the reviewer to attack.

## What this slice delivers
The hook stops being once-per-session and becomes the ambient surface: every grounding moment
consults a local baseline, re-checks the world no more often than a pinned interval, stays
silent only when silence is a verified claim, and speaks exactly the delta when reality
changed ("since you started: PR #7 appeared, touching src/auth/token.py"). CLI and MCP
behavior is unchanged in v1 (stateless one-shots); the delta machinery routes through the
shared classification so those surfaces can adopt it later without a second voice.

## 1. The content-identity digest (pin A1)
New pure-core module `core/content_digest.py`:
`content_digest(signals, statuses, closure) -> str` over EXACTLY: per signal (signal_type,
source_family, scope, evidence_summary, source_display, freshness, confidence, visibility);
per status (source_id, source_family, status, safe_user_message, normal_context_visibility);
per closure entry (proposition, status). Excluded by enumeration: request fields,
`request_id`, `requested_at`, signal `id`/`created_at`/`observed_at`/`expires_at`, status
`last_checked_at`, policy objects (they gate visibility upstream). Sorted, canonical JSON,
sha256. The replay digest is untouched. Tests: one mutation test per included field
(digest changes) and per excluded field (digest stable); covered by the core purity test.

## 2. The ambient edge (`src/teamctx/ambient.py`, the ONE owner of hook state; pin A3)
Owns the baseline store `.teamctx/ambient-state.json` (mode 0600; atomic writes via the
existing pattern; the trackable stanza already ignores it; last-writer-wins on races).

**Key (pin A7):** sha256 over (session_id, resolved repo, forge, branch, sorted normalized
path set, issues, since, docs_root, profile, token-present bool, sha256 of config.json
bytes, teamctx version). Session-scoped on purpose: a new session always re-grounds fully
and gap notices reset. A superset path set is a new key (new baseline), never a match.

**Value:** content_digest; baseline_class (below); last_network_check_at; the minimal
delta material: per check (status, finding identities only: PR/MR numbers + overlapping
paths, issue refs, doc names, gate names; NEVER evidence text, NEVER tokens).

**Interval (pin A3):** `TEAMCTX_AMBIENT_INTERVAL_SECONDS`, default 90, floor 30. Within the
interval no network re-check happens; past it, the next grounding moment re-checks. The
`/tmp` once-per-session marker is DELETED from the codebase; its cost-bound job lives here.

## 3. The silence law implemented (pin A2, with one flagged refinement)
Baseline classes:
- **GOOD**: every important check positively checked (clear or a surfaced finding), coverage
  not shrunk vs the key's first grounding. Silence within the interval is legal and means
  "nothing changed since the good check at {last_network_check_at}".
- **GAP-KNOWN** (the flagged refinement of A2): the answer contains an unreachable, pending,
  or unbounded important check, AND that gap was surfaced to this session already. Strict A2
  would re-surface the gap at EVERY moment; that nags a token-less user on every edit and
  breaks ambient-never-noisy. Refinement: within the interval, silence over a GAP-KNOWN
  baseline is legal and means "you were already told this session that X is unverified;
  nothing else changed". Every interval expiry MUST re-check and MUST speak on any
  transition (gap closed -> "GitHub is back; still clear" / gap persists past a pinned
  re-statement period of 15 minutes -> re-state once). The reviewer is asked to attack this
  refinement specifically.
- **NONE**: no baseline (first moment for the key) -> ground and speak per today's rules.
A re-check failure NEVER downgrades: GOOD stays GOOD (and the failure itself is a new gap
to surface -> transitions to GAP-KNOWN after speaking); errors never produce silence over
an unspoken gap.

## 4. Delta computation and the one seam (pins A5, A6)
After a fresh broker answer, the edge diffs current vs baseline delta material per check:
new finding appeared; finding disappeared (spoken: "PR #7 no longer touches your files");
check transitioned (unreachable->clear, clear->found, pending->clear...); coverage shrank.
Dedup is LAST-VALUE comparison (pin A6): a state that returns to a prior value speaks again.

Minting: the edge builds a delta document of `changed_since_start` signals (scope carries
check id + finding identity + direction), composed into the answer like any connector
document. Classification: `assess()` gains a `deltas` lane populated from these signals
(deltas are notices about already-modeled checks, NOT new certified claims, so NO new
CardKind and no closure/verdict impact; they carry reason codes `delta.<check>.<direction>`).
The shared render and hook_signal speak deltas FIRST, in the one voice; the hook's delta
utterance is one line per change. Copy (CTO-owned, verbatim in the build plan): appear
`since you started: {finding} appeared, touching {paths}`; disappear `since you started:
{finding} cleared`; recovery `{source} is back; {check} is {state}`.

## 5. Grounding moments (pin A4)
- PreToolUse Edit/Write/MultiEdit: as today, now on every event (the cache bounds cost).
- UserPromptSubmit: new entry point in hook.py reading that event's real fields (session_id,
  cwd; no file path). Grounds with the dirty-tree path set (possibly empty: gate/criteria/
  docs still ground; the collision check with zero paths is skipped as not-applicable-
  by-inputs, never a clear). Emits with `hookEventName: "UserPromptSubmit"`.
- Branch switch: NOT an event; the branch lives in the key, so the first moment after a
  switch misses the baseline and re-grounds (test exactly this).
- Build task zero: verify against the pinned minimum Claude Code version (document it in
  the README section for the hook) that PreToolUse and UserPromptSubmit deliver the fields
  used; no other events are consumed.

## 6. What does NOT change
CLI/MCP outputs for a given fresh run; the connectors; the replay digest; the honesty
closure; onboard/status (B1 owns settings placement). The reflex profile budget (one page)
applies to ambient re-checks identically.

## Test bar
Field-enumeration digest tests (1); baseline class transitions incl. never-downgrade and
the GAP-KNOWN refinement matrix (3); key isolation: branch switch, worktree, superset
paths, config edit, version bump, new session (A7/P2-2); interval gating incl. floor;
delta directions incl. reopened-PR re-speak (A6) and disappearance; UserPromptSubmit
empty-tree grounding never clears collision; emit event names per entry point; marker
removal leaves no dead code; hook fail-safe preserved (any error -> exit 0, silence, GOOD
baselines untouched). Harness delta-mode rows land with Workstream E, not this slice.
