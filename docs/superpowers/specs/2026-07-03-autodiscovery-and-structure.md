# Spec: structural consolidation + auto-discovery (2026-07-03)

## Status
Proposed by the CTO (Fable); goes through a codex adversarial spec review before any build.
Covers S6, S7 (structural, built first) and S5a/S5b/S5c (auto-discovery). Sequencing decision
recorded in CURRENT.md: S6+S7 land before S5 because S5b extends the exact registries S6
consolidates; building S5 first would mean immediate rework.

## Goal
After this arc, `teamctx work-start --path <file>` in an onboarded repo fires ALL FOUR checks
with zero extra flags: collision and gate (already automatic), criteria (issue + since derived,
S5a), and docs (relied-on semantics, S5b), with every not-run check carrying a precise,
in-band reason (F9). The CLAUDE.md snippet then claims all four (S5c). Structurally, adding a
card kind or a source becomes a one-entry change (S6) with exactly one card-derivation path (S7).

## S6: registry consolidation (F5, locked design)

One `CardKind` entry carries everything a kind needs; every other table is DERIVED at import.

```python
@dataclass(frozen=True)
class CardKind:
    signal_type: str
    card_predicate: str          # existential; registered shape derived
    query_predicate: str         # universal;  registered shape derived
    verdict_label: str
    check_id: CheckId            # today duplicated in assessment._LABELS
    deps_family: str             # today DEPS_REGISTRY
    severity_base: float         # today severity.KIND_BASE
    refutes_match: Literal["subject-overlap", "repo-wide"]  # NEW: see S5b
    derive: Callable[[RequestContext, SourceSignal], ClaimCard | None]
    query: Callable[[RequestContext], Prop]
    render: Callable[[ClaimCard], ContextCard]
```

Derived at import from `CARD_KINDS` (definitions move next to it; `prop.py` and `severity.py`
re-export or import from the registry owner to avoid an import cycle; the exact home is the
builder's call within "one entry, everything derived"):
- `PREDICATE_REGISTRY = {k.card_predicate: "existential", k.query_predicate: "universal" ...}`
- `REFUTES_PAIRS`/match modes: `{(k.card_predicate, k.query_predicate): k.refutes_match}`
- `DEPS_REGISTRY = {k.query_predicate: frozenset({k.deps_family})}`
- `KIND_BASE = {k.card_predicate: k.severity_base}`
- assessment's `_LABELS = tuple((k.verdict_label, k.check_id) for k in CARD_KINDS)`

Behavior must be byte-identical (the whole suite is the net; zero test-copy changes expected
except imports). Circular-import guard: `assessment.py` imports from core already; `CheckId`
may need to move into core or stay a str in CardKind with a cast at the assessment edge; the
builder proposes, the reviewer checks there is still exactly ONE definition site.

`witnesses()` changes signature-compatibly: for a registered pair, `"subject-overlap"` keeps
today's rule (shared repo + overlapping subject items); `"repo-wide"` refutes on shared repo
alone. All four kinds ship as `"subject-overlap"` in S6 (no behavior change); S5b flips docs.

## S7: forge_review dual-card removal (F4, locked design)

`normalize_forge_review_prs` stops constructing `ContextCard`s (the broker ignores them; the
core derives collision cards in select.py; the two texts have already drifted). The connector
emits signals + statuses + open targets only. Tests asserting on `document.context_cards`
re-point to the core-derived cards (`derive_cards` / `broker_answer`). The dev probe
`github-pr-probe` output shrinks accordingly (its JSON is a raw contract dump; document that
cards are derived downstream). No other connector builds cards (verified in the review).

## S5a: linked-issue + `since` auto-derivation (locked design)

**Privacy boundary is binding: no PR bodies, no comments.** Derivation uses only:
1. **Branch name**: first `#?(\d+)` group in the current branch name in the common shapes
   (`123-fix-x`, `feat/123-x`, `issue-123`, `fix/#123`). A branch with no number derives
   nothing (honest absence). Never derive from branch names like `v2` version tags: require
   the number to be delimited (start, `/`, `-`, `_`, `#`).
2. **Local commit trailers**: closing keywords (`fixes|closes|resolves #N`, case-insensitive)
   in `git log` messages on `merge-base(default_branch, HEAD)..HEAD`. Local git is the user's
   own workspace, not a remote body read. Default branch from
   `git symbolic-ref refs/remotes/origin/HEAD`, falling back to `main` then `master` if those
   refs exist, else honest absence.

`since` = the committer timestamp of `merge-base(default_branch, HEAD)` ("issue changes after
you branched"), ISO-8601 UTC. Detached HEAD, no default branch, or no merge-base: honest
absence.

Precedence (matches the resolution doctrine): explicit `--issue`/`--since` > derived >
honest-absent. Derived values are visible: the work-start render's criteria line names the
derivation ("issue #123 from your branch name") so a wrong guess is judgeable, and `--issue`
overrides it. A derived issue with no derivable `since` falls back to... nothing: the criteria
check needs both; the not-run reason says exactly which half is missing (F9).

New module `src/teamctx/discover.py` (read-only git, same fail-closed conventions as
git_context.py); `resolve_work_start_inputs` calls it when issues/since are not explicit.
The hook inherits automatically (it calls the same resolver).

**F9/F13 absorbed here.** The runner, when it skips a connector for a missing input, now emits
an explicit `disabled` SourceStatus whose `safe_user_message` names the exact missing input
and the exact fix. `assess_completeness` treats a family whose statuses are all `disabled` as
`incomplete[policy-gap]` (we never looked; NOT stale-dep, which would read "couldn't reach").
The render's "Not checked:" line prefers the in-band note from the coverage entry (S1's
note/visibility pass-through) over the static fallback phrase. `since` comparisons normalize
both sides through one parse (`datetime.fromisoformat`, Z-tolerant) instead of lexical string
compare; an unparseable user `since` is a precise input error, not a silent miscompare.

## S5b: docs relied-on semantics (locked design)

Reliance = the team's declared docs set. When `docs_root` is configured, ANY doc under it whose
frontmatter declares `superseded_by` fires a "Verify before relying" card at work-start, no
matter which files the request touches. Rationale: editing a superseded doc is rare; relying
on it while editing code is the real hazard, and the declared docs_root IS the reliance
declaration. Noise is self-limiting: the card names the current doc to use; a team that keeps
a superseded doc forever is choosing to see it (and the hook fires once per session).

Mechanics: docs kind flips to `refutes_match="repo-wide"` (S6's field), so a superseded-doc
claim refutes `no_superseded_docs` on shared repo alone. `not_applicable` narrows to: docs_root
configured, scanned clean, nothing superseded (then the check is `clear`, a real green);
`not_applicable[out-of-scope]` remains only for the scanned-but-nothing-declared-relied case
that S5b removes; if it becomes unreachable, delete it honestly rather than keep dead states.
The `_derive_doc_superseded_claim` gate `doc in request.paths` is removed; the docs connector
already emits one signal per superseded doc. The card copy already names the replacement
(`superseded_by`).

**README/claims update rides the slice** (the docs bullet gets its full strength back).

## S5c: snippet claims all four + copy truthing

`CLAUDE_MD_SNIPPET` expands to claim all four checks (they now auto-fire). The old body moves
into `_KNOWN_BODIES` so onboard migrates marked, unedited old snippets (the S3 classifier
already handles `outdated`). install-hook prints the same new snippet. README quickstart
sample refreshes to a four-check "Checked:" line generated through the real pipeline.

## Test bars (each slice)
- S6: whole suite green with zero behavioral test edits; a new test asserts every derived
  table matches the pre-consolidation literal values (pin-the-refactor test, may be deleted
  after one release).
- S7: no `context_cards` construction outside core; collision copy asserted in exactly one place.
- S5a: derivation matrix (branch shapes incl. non-matches, trailer multi-issue, no-default-
  branch, detached HEAD, explicit-override, derived-visible-in-render); disabled-status reasons
  for each missing-input combination; fromisoformat tolerance (Z, offset, date-only rejected
  or handled, pick one and test it).
- S5b: superseded doc outside request paths fires; clean docs_root reads clear; unreadable root
  stays unreachable-UNKNOWN; symlink-escape still fails closed.
- S5c: snippet migration from both old bodies; README sample regenerated.
