# Spec: the ambient delta engine (Workstream A)

## Status
Revision 2, after an Opus 4.8 adversarial review of rev 1 (verdict REVISE-FIRST: one P0,
six P1, four P2, all accepted; the review also affirmed the deltas-lane-without-a-CardKind
choice, the digest exclusions, and the branch-in-key design, which stand unchanged). The
rev-1 claim that empty-path grounding was already handled was FALSE; section 5 now pins the
fix. Ready for the build plan.

## What this slice delivers
Unchanged from rev 1: the hook becomes the ambient surface with baseline-governed silence
and delta speech; CLI/MCP unchanged in v1.

## 1. The content-identity digest (pins A1 + review P1-1/P1-2/P1-3)
`core/content_digest.py`: `content_digest(signals, statuses, closure, authority) -> str`.
- Signals: computed over the PRE-DELTA answer only; `changed_since_start` signals are
  excluded by type, so baselines never embed prior deltas (P1-1: otherwise silence is
  structurally unreachable).
- Per signal: (signal_type, source_family, scope, evidence_summary, source_display,
  freshness, confidence, visibility). Per status: STRUCTURED facts only: (source_id,
  source_family, status, normal_context_visibility); `safe_user_message` is EXCLUDED (P1-3:
  it embeds run-specific coverage framing like unbounded counts and first-page membership
  that churns on busy repos; any coverage fact that must drive a delta must live in scope
  or status, not free text). Per closure entry: (proposition, status). Per authority entry:
  (subject, state, value) (P1-2).
- Determinism: each item is serialized to canonical JSON (sort_keys) and the ITEM LISTS are
  sorted by that serialized form, so ordering is content-derived and volatile-free (P1-3).
- Tests: one mutation per included field changes it; per excluded field does not; a
  changed_since_start signal does not; authority edits do.

## 2. The ambient edge (pins A3/A7 + review P2-1/P2-2/P2-4)
- **Per-session state files**: `.teamctx/ambient/{session_id}.json` (0600, atomic write via
  a local copy of the tiny mkstemp+replace helper: the edge stays import-light and never
  pulls onboard/connector modules on the no-op path, P2-2). Per-session files remove the
  concurrent-session clobber and make eviction trivial: on every write, files older than 7
  days are deleted (P2-1). First write ensures the directory is gitignored (check-ignore;
  append the ignore if the repo tracks it, mirroring the trackable-stanza mechanics).
- **Corrupt state is NONE**: any read failure (bad JSON, wrong shape, wrong version) is
  caught AT THE READ SITE, treated as no-baseline, and overwritten on the next write; the
  hook's outer fail-safe never becomes a permanent silent death (P2-1).
- **Key**, within the session file: sha256 over (resolved repo, forge, branch, sorted
  normalized path set, issues, since, docs_root, profile, token-present, sha256 of
  config.json bytes CONCATENATED with authority.json bytes (P1-2), teamctx version).
  Superset path sets are new keys, never matches.
- **Testability seams (P2-4)**: the state directory is env-overridable
  (`TEAMCTX_AMBIENT_STATE`), and "now" is injectable internally so Workstream E rows can
  back-date `last_network_check_at` instead of sleeping across the interval floor.
- **Interval**: `TEAMCTX_AMBIENT_INTERVAL_SECONDS`, default 90, floor 30. The `/tmp`
  marker machinery is deleted.

## 3. The silence law (pin A2 + review P1-4)
Baseline classes GOOD / GAP-KNOWN / NONE as rev 1, with the refinement hardened, and the
enumeration CORRECTED post-build: GAP-KNOWN covers ANY surfaced non-positive important check
(unreachable, pending, unbounded, not_configured, not_applicable), not just the first three;
the omission classed a branchless repo NONE and re-spoke on every edit (caught by the
arbiter's live smoke, fixed with a regression test). NONE is strictly the no-baseline
sentinel. The hardened rules:
- **Precedence, pinned:** transition-speak > interval-silence > re-statement-timer. A new
  finding, a disappearance, a coverage shrink, or any class transition ALWAYS speaks at the
  moment it is observed; the timer only governs re-stating the SAME persisting gap.
- **Re-statement period = max(15 minutes, interval)**, evaluated only at interval expiry
  after a REAL re-check; "still couldn't check X" is never said without a fresh attempt
  (P1-4: with a one-hour interval the re-statement rides the hourly re-check; silence in
  between is the documented trade of a user-chosen long interval).
- The cache-served path over GAP-KNOWN remains legal (forbidding it re-opens the nag
  storm); the honesty floor is the guaranteed re-statement backstop.
- Re-check failures never downgrade GOOD silently: the failure is a new gap, spoken once,
  then GAP-KNOWN.

## 4. Deltas through the one seam (pins A5/A6 + review P1-5)
As rev 1 (edge-minted `changed_since_start` signals; an `assess()` deltas lane; NO new
CardKind: the review affirmed this honors the seam), with the interaction pins:
- **Delta direction never changes `kind`**: kind always reflects the current world.
- **A fresh-appearance delta suppresses the steady finding bullet for that item** in the
  same utterance (one fact, one voice: "since you started: PR #7 appeared, touching
  src/auth/token.py" is the finding's appearance, not a second bullet).
- **Deltas emit independently of the ready-guard**: a disappearance or recovery speaks even
  when nothing else is clear and the base render would be empty (the hook_signal `_ready`
  empty-string guard applies to the steady portion only).
- Mapping: appear -> heads_up (bullet suppressed as above); disappear / recovery /
  pending-to-clear -> spoken over the current kind (ready included); coverage-shrank ->
  the current cant_verify with delta framing.

## 5. Grounding moments (pin A4 + review P0-1: the empty-path law)
Rev 1's claim that zero-path grounding was already safe was wrong; the code false-clears
BOTH conflict (empty overlap = no signals = fresh = clear) and gate (FailingGate.files =
request paths, so empty paths derive no card from a genuinely red branch). Pinned fixes,
which are correct product changes independent of ambient:
- **The gate becomes branch-scoped by declaration.** Today `FailingGate.files` is set to
  the request paths, which means the path-overlap gate ALWAYS passes when paths exist; the
  path scoping is vestigial. The missed_gate kind flips to `refutes_match="repo-wide"` and
  its derive drops the path gate (exactly the S5b move for docs); a red branch surfaces no
  matter which files the request names, including none. FailingGate loses its `files`
  field; the card copy keeps naming the check and the branch.
- **Conflict with an empty path set is not-applicable, never clear.** The runner, when the
  normalized path set is empty, does not run the PR probe and emits a `not_applicable`
  git_hosting status with the note `no files in scope yet; open pull requests can't be
  compared until there are paths` (closure `not_applicable[out-of-scope]`; the render's
  existing not-applicable lane speaks it; it never counts as clear).
- UserPromptSubmit grounding (own emit path with `hookEventName: "UserPromptSubmit"`,
  dirty-tree paths, possibly empty) then reads honestly: gate/criteria/docs ground;
  conflict grounds when paths exist and reads not-applicable when none do. The hook copy
  for this entry point is FILE-PATH-FREE (review P2-3): pinned variants "teamctx: before
  you start, from the team's current work:" and "teamctx: looks clear to start
  ({clear phrases})." with no `{file_path}` interpolation.
- Branch switch: derived invalidation via the key, as rev 1 (affirmed).
- Build task zero: verify PreToolUse + UserPromptSubmit fields against the pinned minimum
  Claude Code version; nothing else consumed.

## 6. Cost, stated honestly (review P1-6)
The interval bounds cost PER STABLE KEY (worst case at the 30s floor: ~120 re-checks/hour,
each one GraphQL page + up to two REST calls in reflex profile). A grown path set is a NEW
key and grounds once immediately BY DESIGN: throttling it would silence an unverified new
collision surface. The claim "the cache bounds cost" is corrected to exactly that; the
per-grounding one-page reflex budget is inherited (affirmed on main).

## 7. What does NOT change
As rev 1, minus the gate scoping (now changed deliberately per section 5) and with the
note that CLI work-start with explicit empty paths is impossible today (`--path` required),
so the not-applicable conflict lane is reachable only from the ambient entry points until
a future surface chooses otherwise.

## Test bar
Rev 1's bar, plus: the empty-path matrix (red branch + zero paths -> gate FIRES; zero
paths -> conflict not-applicable with the pinned note, never clear); gate fires on a red
branch while editing unrelated files (the branch-scope change, CLI-visible); digest
pre-delta exclusion; authority edit changes digest and key; safe_user_message churn does
NOT change the digest; per-session file eviction + corrupt-state-is-NONE + ensure-ignore;
re-statement max(15m, interval) with injectable now; the P1-5 trio (bullet suppression,
ready-guard independence, kind stability); file-path-free UserPromptSubmit copy.
