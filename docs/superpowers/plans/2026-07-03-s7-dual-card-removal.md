# S7: Forge-Review Dual-Card Removal Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Exactly one collision-card derivation path. `normalize_forge_review_prs` stops constructing `ContextCard`s (the broker ignores them; the core derives collision cards in select.py; the two texts have already drifted). Spec: `docs/superpowers/specs/2026-07-03-autodiscovery-and-structure.md` section S7 (binding); finding F4.

**Branch:** separate worktree: `git worktree add ../teamctx-s7 -b feat/dual-card-removal main`, all work inside `../teamctx-s7`. Touch ONLY `src/teamctx/connectors/forge_review.py`, `CHANGELOG.md`, and tests. Gate per commit: `python -m pytest -q -p no:cacheprovider && ruff check src tests && python -m mypy src` and `grep -rP '\x{2014}' src tests` empty.

---

### Task 1: Re-point card assertions to the core derivation

**Files:** Modify `tests/test_forge_review.py`, `tests/test_github_truncation.py` (the files asserting on `document.context_cards`).

- [ ] For each test asserting `document.context_cards[...]`, derive the cards the way the product does: `from teamctx.core.select import derive_cards` then `cards = derive_cards(request_context, document.source_signals)` and assert the SAME facts on those (text, `source_body == "status_only"`, reason code `collision.same_path`; the derived card's `source_open_target_id` is None by core design, so assertions on `open_...` ids move to `document.source_open_targets`). Empty-case assertions (`context_cards == []`) become `derive_cards(...) == []` AND `document.context_cards == []` (the field still exists on the contract, now permanently empty from this connector).
- [ ] Run those files: they must still PASS against current main (derived cards carry the same facts). If any assertion CANNOT be satisfied by the derived card (a fact only the connector card carried), STOP and report it; do not weaken the assertion. Commit `test(forge-review): assert collision cards via the core derivation`.

### Task 2: Delete the connector card construction

**Files:** Modify `src/teamctx/connectors/forge_review.py`.

- [ ] Remove the `ContextCard` construction and the `context_cards` accumulation; the document's `context_cards` is always `[]`. Remove now-unused imports (`ContextCard`, and `why_collision_matters` if nothing else uses it; if `collision_summary`/`why_collision_matters` become unused by the connector but are used by tests or core, leave them where the users need them and note it).
- [ ] Full gate. Commit `refactor(forge-review): emit signals/statuses/targets only; cards derive in core (F4)`.

### Task 3: Sweep + CHANGELOG

- [ ] `grep -rn "context_cards" src/teamctx/connectors/` shows no construction anywhere (only the `[]` field fills). CHANGELOG under Changed: `- The GitHub PR connector no longer builds display cards; collision cards derive in the core, so their copy has exactly one home.` Full gate. Commit `docs(changelog): dual-card removal`.

## Completion
Stop after the last commit. Do NOT merge, push, or remove the worktree. Report: branch, commits, gate tail, files changed, deviations. The CTO reviews and merges.
