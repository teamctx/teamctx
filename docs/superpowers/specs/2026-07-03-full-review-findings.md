# Spec: 2026-07-03 full review findings and the build-out arc

## Status
Accepted 2026-07-03 (Edgar approved incorporating all findings and delegating the build).
Source: full code + product + architecture review of main `54ca04e` (428 tests, ruff + mypy
strict green, verified by the reviewer). This doc is the durable home for the findings; the
sequencing lives in `docs/product/plan/CURRENT.md`.

## Review verdict (summary)
The honesty thesis is load-bearing in the code: the three-valued evaluator refuses "clear"
without a complete closure, every connector failure mode routes to an explicit non-fresh
status, and the render surfaces every check status exactly once. No new false-clear path was
found. The findings below are about protecting that property as the product grows.

## Findings (ranked)

### F1. Your own open PR fires a collision against you (P1)
`parse_github_pull_requests` (connectors/github.py:140) never extracts `head`, and
`normalize_forge_review_prs` (connectors/forge_review.py:52) never reads
`request_context.branch`. Any open PR whose changed files overlap the request paths fires a
"Needs attention" collision, including the PR for the branch you are standing on. This will
pollute every actor in the multi-actor dogfood the moment PRs are used.

**Locked design (S1):** parse `head.ref` and `head.repo.full_name`. A PR is "own" only when
its head repo equals the queried repo (forks never match, a deleted-fork null head never
matches) AND its head ref equals the request branch AND the branch is known. Own PRs with
overlap emit no collision signal, no card, no open target; instead the forge-review
SourceStatus records them (scope `own_branch_prs`, message naming the PR, visibility
`warning_when_relevant`) so the fact stays in the observable and is replayable. CoverageEntry
gains a note + visibility pass-through so the render can print one FYI line ("Your own open
PR #N for this branch touches these files; not flagged as a collision."). Clear-phrase copy
becomes "no other open PRs touch your files" (render) / "no other open pull requests touch
these files" (hook) so the clear line stays literally true. The hook's glanceable signal does
not carry the FYI (noise in a one-liner; the full render does). Fail-closed direction: any
missing or malformed head data means "not own", so the PR still surfaces.

### F2. `teamctx status` is a stub that lies (P1, brand)
cli.py:64 unconditionally prints "teamctx is initialized. No sources are configured yet.",
false on all three counts after onboard. For this product a diagnostic that emits fixed
fiction is a brand bug.

**Locked design (S3):** make `status` the read-only twin of onboard's report: config state
and effective repo (via the one shared `resolve_github_repo`), hook presence, credential
source, CLAUDE.md snippet state, live reachability. Zero writes; reuse the onboard step
helpers; never a verdict.

### F3. README predates onboard and overclaims on docs (P1, no-stale-docs rule)
Quickstart teaches `init` + `install-hook` where `onboard` now does both plus snippet,
gitignore stanza, and credential/reachability report. The sample can't-verify output text
does not match the actual render headline. The line "Design or process docs you rely on that
have been superseded" outruns the code: today the docs check fires only when the superseded
doc is itself in the request paths. Fix (S2): onboard-led quickstart, byte-accurate sample
outputs, tighten the docs sentence until the Phase 1 path-gating fix restores it.

### F4. Residual dual card path in forge_review (architecture debt)
forge_review.py builds full ContextCards inside the connector document; the broker ignores
them (`compose` collects signals/statuses/targets/guidance only) and the core independently
derives collision cards in select.py. The two card bodies have already drifted (the core's
reason names the overlapping paths; the connector's does not). Same class as the dual model
killed in June. Fix (S7): delete connector card construction; re-point tests at derived
cards; collision copy gets exactly one home.

### F5. Six hand-synced registries per card kind (architecture debt)
A new kind touches CARD_KINDS (select.py), PREDICATE_REGISTRY + REFUTES_PAIRS (prop.py),
DEPS_REGISTRY (select.py), KIND_BASE (severity.py), and `_LABELS` (assessment.py, which
carries a "keep in sync" comment). A mismatch silently degrades a check to not_configured.
Fix (S6): CardKind carries shape, refutes pair, dependency family, severity base, and
CheckId; derive the other tables from CARD_KINDS at import. One entry, no drift. Do this
before Sprint 4 breadth.

### F6. Malformed `.teamctx/authority.json` crashes with a traceback
connectors/declared_authority.py:18 has no error handling; bad JSON or a missing key
propagates through `work_start_answer` uncaught (CLI traceback, raw MCP tool error, silent
hook swallow). Fix (S4): wrap in the ProjectConfigError pattern with a plain sentence naming
the file and the fix.

### F7. Hook has no end-to-end time bound; PR probe is 1+N requests
The 8s socket timeout bounds each call; a 60-PR repo stalls the first edit ~12s or worse.
The already-tracked server-side path-filtered PR search fixes this AND the truncation copy
(wire `incomplete[unbounded]` end to end). Raised in priority: land as S8 before dogfooding
on any busy repo.

### F8. CI gaps
CI tests 3.12 only while classifiers claim 3.13 (add a matrix entry). pyproject configures
`fail_under = 90` but CI never runs coverage, a gate nobody enforces; wire `pytest --cov`
into CI or delete the config. Fix (S4).

### F9. Criteria not-configured copy is wrong when `--issue` given without `--since`
The static phrase says "no issue is linked to this branch" when the real gap is the
timestamp. Absorbed by Phase 1 auto-discovery (deriving `since` moots it); the phrase logic
should distinguish the missing input as part of that slice.

### F10. `teamctx-mcp` on a base install dies with a raw ImportError
The script is installed without the `mcp` extra. Guard the import with a plain "install
teamctx[mcp]" message. Fix (S4).

### F11. `_gh_hint` prints `gh pr view N` without `--repo`
contract_render.py:140; inconsistent with `open-source`, which includes it. Fix (S2, with
the README sample sync).

### F12. `expires_at="next_refresh"` is a magic string in a timestamp-typed field
Fine for v0; noted for schema v1. No action this arc.

### F13. Issue-events pagination and lexical `since` comparison
`_classify_changes` reads the first 100 events with no truncation flag (worst case
misclassifies the change kind; updated_at already fired, so never a false clear). The
`updated_at <= since` string comparison assumes matching ISO shapes. Both absorbed by Phase 1
auto-discovery, which derives `since` by construction.

## Product observations carried into the arc
- Only two of four checks fire without manual flags today; Phase 1 auto-discovery is the
  moment the product becomes what the README describes.
- "Docs you rely on" is currently "docs you edit" (see F3); the Phase 1 path-gating fix is
  the real close.
- Collision value at wedge scale needs teammates' PRs; the multi-actor emulation is the
  critical validation and requires F1 fixed first.
- Reflex staleness window (once per session) stays as designed; revisit with dogfood
  evidence.
