# Check Catalog Spine Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build the catalog spine per `docs/superpowers/specs/2026-07-07-check-catalog-spine-design.md` REVISION 5 (ROCK-SOLID, Edgar-approved 2026-07-08). Every pin in that spec is law; its four dispositions explain why.

**Architecture:** Seven stacked slices, each independently merged, the emulation oracle GREEN after every slice (16 rows through slice 4, growing to 21 by slice 7). Byte-identity is the bar for slices 1-3; new loud lines land only where the spec names them.

**The one law over all slices:** no path from no-data to a clear; a broken/unknown config SPEAKS, it never silences; rendered bytes for unchanged worlds never change except spec-named lines.

## Slice sequence (one builder at a time; each slice = one worktree branch, merged before the next starts)

### Slice 1: the ClosureEntry projection seam (`feat/spine-closure-seam`)
core/contracts.py + core/select.py: closure entries become
(check_id, proposition, consumed_document_ids sorted, closure_status, reason) with a
`(proposition, status)` PROJECTION consumed by evaluate, content_digest, and render, so all
bytes and digests are unchanged. content identity keeps taking (proposition, status) ONLY
(spec round-3 P1-4). Tests: projection equivalence property (every existing closure test
passes through both shapes); ambient state schema version bump with old-baselines-read-as-none
test. Gate + 16/16.

### Slice 2: document identity and ownership (`feat/spine-doc-identity`)
Documents gain stable ids and types (connectors/_contract.py, core/broker.py); fetch status
belongs to source/document, verifiedness to checks; uniqueness validated; the current four
checks map 1:1 (behavior identical; the N:M capability is exercised in slice 6's oracle row).
Snapshot/replay digest untouched (spec: closure never fed it). Gate + 16/16 byte-identical.

### Slice 3: the check contract (`feat/spine-contract`)
core/kinds.py evolves into the contract module: declarations carry id, contract_version,
claim, consumes, derive (pure), closure propositions, the copy table (finding copy incl.
(source_id,status) coverage notes + provenance hooks + delta templates; ADVISORY copy lives
with source contracts per round-2 P2-9), identity fields, profile, lane, config_schema.
Migration task zero: inventory EVERY existing rendered string into the tables (the four
checks re-declared; contract_render/hook_signal consume declarations). Conformance suite:
purity, closure completeness, copy law (em-dash grep), determinism, mutation test per claim
input, and the identity round-trip through compute_baseline_material + delta (round-3 P1-7).
Gate + 16/16 byte-identical (the oracle is the proof of migration).

### Slice 4: committed-blob reads and loud config failure (`feat/spine-blob-config`)
Team semantics (config.json AND authority.json) read from `git -C <root> show HEAD:<path>`
on normal surfaces; five states (committed_clean, committed_dirty, uncommitted_refused,
no_git_or_no_head_refused, allow_dirty) feed the ambient key; pinned dirty-note copy ("using
the committed HEAD config; working-tree config changes take effect when committed");
never-committed/no-git = default four + loud line; deleted-but-committed honors HEAD.
`work-start --allow-dirty` (full selection, explicit banner). ONE shared config-failure
formatter for CLI/MCP/hook; the hook catches ProjectConfigError inside _run and EMITS the
loud line (fail-safe keeps eating only unexpected errors). New oracle rows: untracked-config
(default four + loud line), hook-speaks-on-unknown-check, dirty-authority. Gate + 19/19.

### Slice 5: team selection (`feat/spine-selection`)
The `checks` block (spec section 3 shape, absent = default four); enabled-set filters
assessment/render/runner document resolution; lane overrides feed the silence law's
important-set; version-skew rules (unknown anything = loud failure; requires_teamctx);
the not-enabled coverage summary line (data half; one line, never a confession, never
silence). New oracle rows: checks-block-honored, disabled-check-visible. Gate + 21/21.

### Slice 6: declared file sources and declared checks (`feat/spine-declared`)
The generic connector, file kind only (URL = v1.1, designed not built): relative path,
root-resolved, symlink-escape rejected, not under .git, regular file, size cap, GIT-TRACKED
(read via HEAD blob like config); schema_map JSON-pointer plucking with per-field length
caps, control-char stripping, depth/size caps, duplicate-key rejection (one strict parser).
Declared checks: claim, match algebra (equality/presence/prefix/threshold; total; missing
field = couldn't-fully-check), time operands (request.requested_at + document observed_at,
ISO-8601 UTC, malformed = couldn't-fully-check), copy, consumes, identity, lane, profile
all EXPLICIT; x_ id namespace + casefold collision + reserved built-in names/phrases
(shadowing closed); conformance at config load with plain errors through the shared
formatter. THE PROOF ROW: one declared file source consumed by TWO declared checks, one
shared fetch, two per-check closures incl. the failure case (N:M tested; build risk #1
closed). Rows also exercise not-enabled summary + tracked-file refusal. Gate + matrix green
(this slice's rows numbered by the builder; runner registry updated).

### Slice 7: migration cleanup (`feat/spine-cleanup`)
MCP tool schema drops repo/docs_root (CHANGELOG, breaking pre-1.0); work-start flags
documented as diagnostic; rows/tests that passed overrides migrate to committed-config
fixtures; docs: user-guide gains the checks-block paragraph and the declared-source recipe
(claims-reviewed before merge); CHANGELOG entries for every slice; the spec's status flips
to BUILT with the merge hashes. Full gate + full matrix + em-dash grep repo-wide.

## Builder discipline (every slice)
Worktree per slice; TDD per task; gates as SEPARATE commands with real exit codes
(pytest -q, ruff, mypy --strict, em-dash grep, `python emulation/runner.py --offline --all`);
coverage >= 90; copy strings VERBATIM from the spec (the CTO owns every string); on
plan-vs-spec contradiction STOP and record; no merge/push (the CTO arbiter merges).
