# Spec: structural consolidation + auto-discovery (2026-07-03)

## Status
Revision 2, after a codex adversarial spec review (verdict on rev 1: REVISE-FIRST, no P0,
six P1 + three P2, all accepted by the CTO-arbiter and pinned below). Ready to build.
Covers S6, S7 (structural, built first) and S5a/S5b/S5c (auto-discovery). Sequencing
decision recorded in CURRENT.md: S6+S7 land before S5 because S5b extends the exact
registries S6 consolidates.

## Goal
After this arc, `teamctx work-start --path <file>` in an onboarded repo fires ALL FOUR checks
with zero extra flags: collision and gate (already automatic), criteria (issue + since derived,
S5a), and docs (relied-on semantics, S5b), with every not-run check carrying a precise,
in-band reason (F9). The CLAUDE.md snippet then claims exactly what fires (S5c). Structurally,
adding a card kind or a source becomes a one-entry change (S6) with exactly one card-derivation
path (S7).

## S6: registry consolidation (F5; design pinned, review P1-1 and P1-2)

### The one registry owner: `src/teamctx/core/kinds.py` (new)
Pinned dependency direction (no cycles, one definition site per fact):

- `core/prop.py` keeps the pure DATATYPES and MECHANISM only: `Prop`, `SubjectRef`,
  `Witness`, and a parameterized `witnesses_with(claim, query, refutes_match)` helper.
  Its tables (`PREDICATE_REGISTRY`, `REFUTES_PAIRS`) and `Prop.shape` MOVE OUT.
- `core/severity.py` keeps the MECHANISM only: `compute_severity(kind_base, claim)`
  takes the base as an argument; `KIND_BASE` moves out.
- `core/kinds.py` imports contracts, prop, severity. It defines `CheckId` (moves here from
  assessment.py), `CardKind`, the four kinds' derive/render functions (moved from select.py,
  including `_render_claim_card`), `CARD_KINDS`, and DERIVES everything else at import:
  `shape_of(prop)` (raising on unregistered predicates exactly as `Prop.shape` does today),
  `witnesses(claim, query)` (dispatching each registered pair's `refutes_match` through
  `prop.witnesses_with`), `deps_for(prop)`, `severity_base_for(predicate)`,
  `reason_prefix` routing, and the `(verdict_label, check_id)` pairs assessment consumes.
- `core/select.py` keeps the ENGINE only (projection, derive dispatch, coverage, closure,
  `select_context`), importing kinds. `core/evaluate.py` switches `query.shape` to
  `kinds.shape_of(query)`. `assessment.py` imports `CheckId` and the label pairs from kinds
  (it already imports core; kinds imports no application module, so no cycle).

```python
@dataclass(frozen=True)
class CardKind:
    signal_type: str
    card_predicate: str            # existential
    query_predicate: str           # universal
    verdict_label: str
    check_id: CheckId
    reason_prefix: str             # "collision" | "criteria" | "doc" | "gate" (assessment routing)
    deps_family: str
    severity_base: float
    refutes_match: Literal["subject-overlap", "repo-wide"]
    derive: Callable[[RequestContext, SourceSignal], ClaimCard | None]
    query: Callable[[RequestContext], Prop]
    render: Callable[[ClaimCard], ContextCard]
```

### Render copy stays human, but its completeness is enforced (P1-2)
Per-check copy remains hand-written at the render edge (voice is owned by the CTO), but it
consolidates into one struct so a new kind cannot silently lack copy:

```python
@dataclass(frozen=True)
class CheckCopy:            # in contract_render.py, one entry per CheckId
    clear: str              # today _CLEAR_PHRASE
    not_checked: str        # today _NOT_CHECKED_PHRASE (static fallback; see S5a note carrier)
    unreachable: str        # today _UNREACHABLE_PHRASE
    finding_action: str     # today _FINDING_ACTION
    hook_clear: str         # today hook_signal._CLEAR_PHRASE
    hook_gap: str | None    # today hook_signal._HOOK_GAP (None = not an important check)
```

`RENDER_COPY: dict[CheckId, CheckCopy]`, plus an import-time check (and a test) that
`set(RENDER_COPY) == {k.check_id for k in CARD_KINDS}`: a kind without copy fails loud at
import, never silently drops from the report. `hook_signal` reads the same struct.
(`_PENDING_PHRASE` / `_NOT_APPLICABLE_PHRASE` keep their per-check overrides with generic
fallbacks, unchanged.)

### Behavior bar
Byte-identical output; the whole suite passes with import-path edits only. A pin-the-refactor
test asserts every derived table equals the pre-consolidation literals. The core purity test
covers kinds.py. All four kinds ship `refutes_match="subject-overlap"` (S5b flips docs later).

## S7: forge_review dual-card removal (F4, unchanged from rev 1)

`normalize_forge_review_prs` stops constructing `ContextCard`s (the broker ignores them; the
core derives collision cards; the two texts have already drifted). The connector emits
signals + statuses + open targets only. Tests asserting `document.context_cards` re-point to
core-derived cards. No other connector builds cards (reviewer verified).

## S5a: linked-issue + `since` auto-derivation (pins from P1-4, P1-5, P2-7, P2-8, P2-9)

**Privacy boundary (pinned wording):** no REMOTE bodies ever (PR/issue bodies, comments,
patches: unchanged exclusion). Local commit messages are the user's own workspace metadata;
the parser extracts ONLY closing-keyword issue numbers; messages are never stored, surfaced,
or sent anywhere. If `docs/engineering/build-plan.md`'s exclusion wording reads as forbidding
local commit-message parsing, update it in the same slice to say exactly this (provenance
preserved).

**Derivation (pinned, executable):** new module `src/teamctx/discover.py`, read-only git,
fail-closed conventions of git_context.py.
- Branch: first match of `(?:^|[/_-])#?(\d{1,6})(?=[/_-]|$)` against the branch name,
  rejected when the digits are immediately preceded by `v` or `V` (release branches).
- Trailers: every match of `\b(?:fixes|closes|resolves)\s+#(\d{1,6})\b` (case-insensitive)
  in `git log --format=%B merge-base..HEAD` messages.
- Result = union of both, deduped, numerically sorted, capped at 5 (a cap hit is recorded in
  the disabled/derived note, never silent).
- `since` = committer timestamp of `merge-base(default_branch, HEAD)`, ISO-8601 UTC. Default
  branch: `git symbolic-ref refs/remotes/origin/HEAD`, else `main`, else `master` (existing
  refs only), else honest absence. Detached HEAD or no merge-base: honest absence.
- Precedence unchanged: explicit > derived > honest-absent. Explicit `--issue` disables ALL
  issue derivation (no mixing); explicit `--since` disables since-derivation.

**`since` parsing (pinned):** both sides of every comparison go through one
`parse_since(text)` using `datetime.fromisoformat` (3.12 accepts `Z`); naive values are
assumed UTC; date-only input is ACCEPTED as midnight UTC. Unparseable explicit `--since` is a
precise input error at resolve time (ClickException path), never a silent lexical compare.

**Provenance carrier (P1-5, pinned):** `RequestContext` gains
`input_provenance: dict[str, str] = {}` (schema-additive; e.g. `"issue:#123": "your branch
name"`, `"issue:#7": "a commit message trailer"`, `"since": "when you branched (merge-base
abc1234)"`). The replay digest already hashes the whole request, so provenance is bound
automatically. `BrokerAnswer` gains `request: RequestContext` so the render can see it. The
criteria line names derived inputs: clear reads "the linked issue's criteria are unchanged
(issue #123 from your branch name)"; a finding's card copy is unchanged (the card already
names the issue).

**Missing-input notes reach the render (P1-4, pinned):** when the runner skips a connector it
emits a `disabled` SourceStatus whose `safe_user_message` names the exact missing input and
fix ("no issue could be derived from your branch or commits; name one with --issue", "an
issue was derived but the start time could not be (no merge-base); pass --since"). Mapping:
`assess_completeness` treats a family whose present statuses are ALL `disabled` as
`incomplete[policy-gap]` (never stale-dep). `CheckState` gains `note: str | None`; `assess()`
fills it from the disabled coverage entry of the check's `deps_family` (S1's CoverageEntry
note field). `_not_checked_line` prefers `state.note` over the static `CheckCopy.not_checked`
fallback. F9's wrong copy dies here; F13's lexical compare dies above.

## S5b: docs relied-on semantics (pins from P1-3)

Reliance = the declared docs set. With `docs_root` configured, ANY doc under it whose
frontmatter declares `superseded_by` fires a "Verify before relying" card, regardless of
request paths. Mechanics: docs kind flips to `refutes_match="repo-wide"`; the
`doc in request.paths` gate in the derive function is removed.

**Honesty pins (P1-3):** a configured, readable, clean docs scan emits `fresh` (a real green:
"the docs you rely on are current"). The docs connector STOPS emitting `not_applicable`
entirely (with reliance = the whole declared set, out-of-scope no longer exists for docs).
`not_applicable` is NEVER mapped to clear anywhere; the contract literal and its
assessment/render handling remain for future kinds; `not_applicable[out-of-scope]` handling
in `assess_completeness` stays as-is (dead for docs, correct in general). Unreadable root and
symlink-escape keep failing closed to unavailable/UNKNOWN.

README's docs bullet gets its full strength back in the same slice.

## S5c: onboard detects docs, snippet claims exactly what fires (pins from P1-6)

- **onboard gains docs detection:** if a top-level `docs/` directory exists containing at
  least one `*.md` (recursive), onboard writes `docs_root: "docs"` into the config it creates
  and reports it as its own step ("docs: found a docs/ folder; superseded docs there will be
  flagged"). No docs folder: the step reports how to enable it. Existing configs are NOT
  modified (the config step's existing already/force semantics are untouched).
- **Snippet copy states conditions, not wishes (final copy, CTO-owned):** claims open PRs and
  failing checks unconditionally; criteria "when an issue is linked from your branch or
  commits"; docs "when a docs folder is configured". The old snippet bodies join
  `_KNOWN_BODIES` so the S3 classifier migrates unedited old blocks (`outdated` state).
- README quickstart sample regenerates through the real pipeline with all four checks firing.

## Test bars
- S6: suite green with import-path-only edits; pin-the-refactor equality test; copy
  completeness test; purity test covers kinds.py.
- S7: no card construction outside core; collision copy asserted in exactly one place.
- S5a: derivation matrix (branch shapes incl. `v2` rejection and delimiter rules, trailer
  multi-issue + cap, union/dedupe/sort, no-default-branch, detached HEAD, explicit-override
  disables derivation, provenance rendered on clear lines, disabled-note per missing-input
  combination, date-only and Z-suffix since, unparseable explicit since errors precisely).
- S5b: superseded doc outside request paths fires; clean scan reads the real green; docs
  connector emits no not_applicable; unreadable root and symlink-escape stay UNKNOWN.
- S5c: docs/ detection on/off; config-untouched-when-existing; snippet migration from all
  prior known bodies; README sample regenerated.
