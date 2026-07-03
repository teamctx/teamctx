# S6: Registry Consolidation Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** One `CardKind` entry per card kind carries every fact about it; every other table (predicate shapes, refutes pairs, deps, severity bases, assessment labels, reason prefixes) is DERIVED at import. Byte-identical behavior; adding a kind becomes a one-entry change.

**Architecture:** BINDING design in `docs/superpowers/specs/2026-07-03-autodiscovery-and-structure.md` section S6 (revision 2, review-hardened). The pinned dependency direction: `prop.py` and `severity.py` keep pure mechanisms (no tables); new `core/kinds.py` owns `CheckId`, `CardKind`, the four kinds' derive/render functions, `CARD_KINDS`, and all derived lookups; `select.py` keeps the engine; `evaluate.py` uses `kinds.shape_of`; `assessment.py` imports `CheckId` + label pairs from kinds; render copy consolidates into `CheckCopy`/`RENDER_COPY` in contract_render.py with an import-time completeness check, and `hook_signal.py` reads the same struct.

**Tech Stack:** Python 3.12. Gate per commit: `python -m pytest -q -p no:cacheprovider && ruff check src tests && python -m mypy src` and `grep -rP '\x{2014}' src tests` empty.

**Branch:** separate worktree: `git worktree add ../teamctx-s6 -b feat/registry-consolidation main`, all work inside `../teamctx-s6`.

**Prime directive:** this is a REFACTOR. Every behavioral test in the suite must pass with import-path-only edits. If a test needs a behavioral change, STOP and report; do not adapt the test.

---

### Task 1: Pin-the-refactor test (write BEFORE moving anything)

**Files:** Create `tests/test_kinds_registry.py`.

- [ ] Write a test that snapshots today's literal tables as expected values and asserts the (future) derived lookups equal them. Concretely, hardcode the current contents of `PREDICATE_REGISTRY` (8 entries), `REFUTES_PAIRS` (4 pairs), `DEPS_REGISTRY` (4 entries), `KIND_BASE` (4 entries), and assessment's `_LABELS` (4 pairs) as literals in the test, importing them from their CURRENT homes so the test passes on main first. Run it: PASS. Commit `test(kinds): pin current registry contents before consolidation`.

### Task 2: Mechanisms extracted (prop, severity)

**Files:** Modify `src/teamctx/core/prop.py`, `src/teamctx/core/severity.py`; Create `src/teamctx/core/kinds.py` (skeleton).

- [ ] `prop.py`: keep `Prop`, `SubjectRef`, `Witness`, `PropShape`; add `witnesses_with(claim, query, match)` where `match` is `"subject-overlap"` (today's rule: shared repo + overlapping subject items) or `"repo-wide"` (shared repo alone). Remove `PREDICATE_REGISTRY`, `REFUTES_PAIRS`, `Prop.shape`, and the old `witnesses`.
- [ ] `severity.py`: `compute_severity(kind_base: float, claim: Prop) -> Severity` (base as an argument); remove `KIND_BASE` and the predicate lookup.
- [ ] `kinds.py`: define `CheckId` (moved from assessment.py), the `CardKind` dataclass exactly as the spec pins it, move the four derive/render functions + `_render_claim_card` from select.py, define `CARD_KINDS` (all four kinds, `refutes_match="subject-overlap"`), and derive: `shape_of(prop)` (ValueError on unregistered, same message contract as the old `Prop.shape`), `witnesses(claim, query)`, `deps_for(prop)` (ValueError on unregistered, same contract as old), `severity_base_for(predicate)`, `label_check_pairs()` or an equivalent tuple, and a `reason_prefix` mapping. Renders call `compute_severity(severity_base_for(...), claim)`.
- [ ] Update `select.py` (engine keeps `derive_claims`/`render_claim`/`derive_cards`/coverage/closure/`select_context`, importing from kinds), `evaluate.py` (`kinds.shape_of(query)`), `assessment.py` (import `CheckId` + pairs + reason prefixes from kinds), `core/__init__.py` re-exports if any break. Keep temporary compatibility aliases ONLY if a test imports the old name from the old home; prefer updating the test import.
- [ ] Update the pin test's imports to the new homes (the literal expected values DO NOT change). Full gate. Commit `refactor(core): kinds.py owns the card-kind registry; tables derived from CARD_KINDS`.

### Task 3: Render copy completeness (CheckCopy)

**Files:** Modify `src/teamctx/contract_render.py`, `src/teamctx/hook_signal.py`; extend `tests/test_kinds_registry.py`.

- [ ] Consolidate `_CLEAR_PHRASE`, `_NOT_CHECKED_PHRASE`, `_UNREACHABLE_PHRASE`, `_FINDING_ACTION` (contract_render) and `_CLEAR_PHRASE`, `_HOOK_GAP` (hook_signal) into one `RENDER_COPY: dict[CheckId, CheckCopy]` in contract_render.py per the spec's `CheckCopy` fields; hook_signal imports it. Copy strings are VERBATIM today's strings (this task changes zero output bytes).
- [ ] Import-time completeness: after `RENDER_COPY` is defined, a module-level check raises if `set(RENDER_COPY) != {k.check_id for k in CARD_KINDS}`; plus a test asserting the same and a test that `hook_gap` is non-None exactly for `IMPORTANT_CHECKS`.
- [ ] Full gate (the render/hook test files must pass UNCHANGED). Commit `refactor(render): one RENDER_COPY per check, completeness enforced at import`.

### Task 4: Purity + sweep

- [ ] Confirm the core purity test covers `kinds.py` (extend its module list if it enumerates); `grep -rn "PREDICATE_REGISTRY\|REFUTES_PAIRS\|KIND_BASE\|DEPS_REGISTRY" src tests` finds only kinds.py definitions/derivations + the pin test. CHANGELOG under Changed: `- Internal: card kinds are now a single registry (core/kinds.py); adding a kind is a one-entry change. No behavior change.` Full gate. Commit `docs(changelog): registry consolidation`.

## Completion
Stop after the last commit. Do NOT merge, push, or remove the worktree. Report: branch, commits, gate tail, files changed, deviations. The CTO reviews and merges.
