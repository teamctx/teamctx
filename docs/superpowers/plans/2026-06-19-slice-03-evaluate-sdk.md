# Slice 3 — Consumer SDK `evaluate(ρ, C, κ)` Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Ship the sound consumer rule — `evaluate(query, C, κ) → Valuation` — that under-approximates the three-valued semantics, turning observable soundness (Theorem 2) from prose into tested code. Expose the typed certified claims (`C`) on the broker's answer so the SDK runs against a real selection.

**Architecture:** A new pure module `core/evaluate.py` holds `Valuation` and `evaluate`. It reads only typed structure: a card's `claim` polarity (via `witnesses` from slice 1) and the per-proposition `closure` (from slice 2). The broker's `ContextSelection` gains `claim_cards` (the typed `C`) alongside the rendered cards. No CLI/render changes in this slice (the human-plane verdict line is slice 3.5), which keeps the import graph acyclic: `evaluate.py → select.py, prop.py` (one-way; `select.py` does NOT import `evaluate.py`).

**Tech Stack:** Python 3.12, frozen dataclasses + `typing.Literal`, pytest, ruff, mypy --strict.

---

## Context the implementer needs

- Slice 1 (`core/prop.py`): `Prop` (with `.shape` ∈ `universal|existential` from a registry), `witnesses(claim, query) -> "supports"|"refutes"|"unrelated"`. Today only `refutes`/`unrelated` are ever produced; `supports` is reserved.
- Slice 2 (`core/select.py`): `ClaimCard` (`claim: Prop`, `signal: SourceSignal`), `derive_claims(request, signals) -> list[ClaimCard]`, `no_conflict_query(request) -> Prop` (the universal `no_pr_conflicts_with_paths`), `Completeness`, `ClosureEntry` (`proposition: str`, `status: Completeness`), `assess_completeness`, and `ContextSelection` (fields `cards`, `coverage`, `closure`). `select_context(request, signals, statuses)` builds the selection.
- The core purity test globs `src/teamctx/core/*.py`; `evaluate.py` must import only `dataclasses`, `typing`, and internal `teamctx.core.*` modules (no os/pathlib/time/etc.).
- The collision query is a **universal** ("no PR conflicts with my paths"). A collision `ClaimCard` `refutes` it (counterexample → the universal is False).

---

## File structure

- **Create `src/teamctx/core/evaluate.py`** — `Valuation` (frozen) + `evaluate(query, claim_cards, closure)`. The consumer rule. One responsibility.
- **Modify `src/teamctx/core/select.py`** — add `claim_cards: tuple[ClaimCard, ...]` to `ContextSelection`; populate it in `select_context`.
- **Create `tests/test_evaluate.py`** — unit soundness tests for `evaluate` with hand-built inputs.
- **Modify `tests/test_select.py`** — end-to-end tests: `evaluate` against a real `select_context` output.

---

## Task 0: Branch and commit the plan

- [ ] `git checkout -b build/slice-03-evaluate-sdk`
- [ ] `git add docs/superpowers/plans/2026-06-19-slice-03-evaluate-sdk.md && git commit -m "docs: slice-03 plan (consumer SDK evaluate)"`

---

## Task 1: The consumer rule (`core/evaluate.py`)

**Files:** Create `src/teamctx/core/evaluate.py`; Create `tests/test_evaluate.py`.

- [ ] **Step 1: Write the failing tests.** Create `tests/test_evaluate.py`:
```python
"""Unit tests for the sound consumer rule (Theorem 2 in code)."""

from __future__ import annotations

from teamctx.connectors.forge_review import ForgeReviewPullRequest, normalize_forge_review_prs
from teamctx.core.contracts import RequestContext
from teamctx.core.evaluate import Valuation, evaluate
from teamctx.core.prop import Prop, SubjectRef
from teamctx.core.select import ClaimCard, ClosureEntry, derive_claims, no_conflict_query


def _request(paths: tuple[str, ...]) -> RequestContext:
    return RequestContext(
        schema_version="teamctx.request_context.v0",
        request_id="r",
        repo="svc",
        task="t",
        paths=list(paths),
        requested_at="2026-01-01T00:00:00Z",
    )


def _collision_claim_card(path: str) -> ClaimCard:
    request = _request((path,))
    pr = ForgeReviewPullRequest(
        provider="github",
        repo="svc",
        number=1,
        state="open",
        url="https://example/pr/1",
        title=None,
        changed_paths=(path,),
        created_at="2026-01-01T00:00:00Z",
        updated_at="2026-01-01T00:00:00Z",
    )
    document = normalize_forge_review_prs(request, [pr], observed_at="2026-01-01T00:00:00Z")
    # derive_claims yields the typed collision claim for the overlapping PR.
    return derive_claims(request, document.source_signals)[0]


def _closure(status: str) -> tuple[ClosureEntry, ...]:
    return (ClosureEntry(proposition="no_pr_conflicts_with_paths", status=status),)


def test_universal_is_false_by_counterexample_even_if_coverage_incomplete() -> None:
    query = no_conflict_query(_request(("a.py",)))
    claim_cards = (_collision_claim_card("a.py"),)
    # a real conflict exists -> False, regardless of closure (counterexample falsifies it).
    assert evaluate(query, claim_cards, _closure("incomplete[policy-gap]")) == Valuation("false")


def test_universal_is_true_only_under_complete_closure_with_no_counterexample() -> None:
    query = no_conflict_query(_request(("a.py",)))
    assert evaluate(query, (), _closure("complete")) == Valuation("true")


def test_universal_is_unknown_when_closure_incomplete_and_no_counterexample() -> None:
    query = no_conflict_query(_request(("a.py",)))
    # absence of a refuting card NEVER licenses True — gated on completeness.
    assert evaluate(query, (), _closure("incomplete[policy-gap]")) == Valuation(
        "unknown", "incomplete[policy-gap]"
    )
    assert evaluate(query, (), _closure("incomplete[stale-dep]")) == Valuation(
        "unknown", "incomplete[stale-dep]"
    )


def test_universal_is_unknown_when_no_closure_entry_for_the_query() -> None:
    query = no_conflict_query(_request(("a.py",)))
    # no closure assessed for this query -> conservatively not complete.
    assert evaluate(query, (), ()) == Valuation("unknown", "incomplete[policy-gap]")
```

- [ ] **Step 2: Run** `pytest tests/test_evaluate.py -v` — expect FAIL: `No module named 'teamctx.core.evaluate'`.

- [ ] **Step 3: Implement.** Create `src/teamctx/core/evaluate.py`:
```python
"""The sound consumer rule: evaluate a query proposition against the broker's answer.

This is where observable soundness (Theorem 2) becomes code, not prose. Given a query
``rho``, the typed certified claims ``C`` (claim cards), and the coverage closure
``kappa``, ``evaluate`` under-approximates the three-valued semantics: it answers True or
False only when justified — by a witness, or by exhaustive absence under a *complete*
closure — and Unknown otherwise. The absence-branch gates on completeness: the absence of
a refuting card never licenses "clear".

Pure: dataclasses, typing, and internal core imports only (the core purity test guards it).
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Literal

from teamctx.core.prop import Prop, witnesses
from teamctx.core.select import ClaimCard, ClosureEntry


@dataclass(frozen=True)
class Valuation:
    """A three-valued verdict for a query. ``reason`` is set only when value is 'unknown'."""

    value: Literal["true", "false", "unknown"]
    reason: str = ""


def _closure_status(query: Prop, closure: tuple[ClosureEntry, ...]) -> str:
    for entry in closure:
        if entry.proposition == query.predicate:
            return entry.status
    # No closure assessed for this query -> conservatively treat as not complete.
    return "incomplete[policy-gap]"


def evaluate(
    query: Prop,
    claim_cards: tuple[ClaimCard, ...],
    closure: tuple[ClosureEntry, ...],
) -> Valuation:
    """Soundly under-approximate the truth of ``query`` from the broker's answer ``<C, kappa>``."""

    supports = any(witnesses(card.claim, query) == "supports" for card in claim_cards)
    refutes = any(witnesses(card.claim, query) == "refutes" for card in claim_cards)

    if supports and refutes:
        return Valuation("unknown", "conflicting-evidence")

    status = _closure_status(query, closure)
    if query.shape == "universal":
        if refutes:
            return Valuation("false")  # one counterexample falsifies a universal
        if status == "complete":
            return Valuation("true")  # exhaustive absence under a complete closure
        return Valuation("unknown", status)
    # existential
    if supports:
        return Valuation("true")
    if status == "complete":
        return Valuation("false")
    return Valuation("unknown", status)
```

- [ ] **Step 4: Run** `pytest tests/test_evaluate.py -v` — expect PASS (4 tests).

- [ ] **Step 5: Commit**
```bash
git add src/teamctx/core/evaluate.py tests/test_evaluate.py
git commit -m "feat: sound consumer rule evaluate(query, C, kappa) -> Valuation"
```

---

## Task 2: Expose the typed claims (`C`) on the broker's answer

**Files:** Modify `src/teamctx/core/select.py`; Modify `tests/test_select.py`.

- [ ] **Step 1: Write the failing tests.** In `tests/test_select.py`, add `evaluate`/`Valuation` import: `from teamctx.core.evaluate import Valuation, evaluate`. Append:
```python
def test_select_context_exposes_typed_claim_cards() -> None:
    document = load_document()
    selection = select_context(
        document.request_context, document.source_signals, document.source_statuses
    )
    assert len(selection.claim_cards) == 1
    assert selection.claim_cards[0].claim.predicate == "pr_conflicts_with_path"


def test_evaluate_against_a_real_selection_is_false_when_a_collision_is_present() -> None:
    document = load_document()
    selection = select_context(
        document.request_context, document.source_signals, document.source_statuses
    )
    verdict = evaluate(
        no_conflict_query(document.request_context),
        selection.claim_cards,
        selection.closure,
    )
    # the fixture has a collision card -> a real conflict -> False (a counterexample).
    assert verdict == Valuation("false")


def test_evaluate_against_a_real_selection_is_unknown_when_clear_but_coverage_gapped() -> None:
    document = load_document()
    request = document.request_context.model_copy(update={"paths": ["src/nothing/here.py"]})
    selection = select_context(request, document.source_signals, document.source_statuses)
    verdict = evaluate(no_conflict_query(request), selection.claim_cards, selection.closure)
    # no collision card, but git_hosting is unobserved -> Unknown, never a false "clear".
    assert selection.claim_cards == ()
    assert verdict == Valuation("unknown", "incomplete[policy-gap]")


def test_evaluate_against_a_real_selection_is_true_when_clear_and_coverage_complete() -> None:
    document = load_document()
    request = document.request_context.model_copy(update={"paths": ["src/nothing/here.py"]})
    selection = select_context(request, document.source_signals, [_git_hosting_status("fresh")])
    verdict = evaluate(no_conflict_query(request), selection.claim_cards, selection.closure)
    # no collision card AND the mandated source is fresh -> certified clear.
    assert verdict == Valuation("true")
```
(`_git_hosting_status` and `no_conflict_query` already exist in this file from slice 2.)

- [ ] **Step 2: Run** `pytest tests/test_select.py -v` — expect FAIL: `ContextSelection` has no `claim_cards`.

- [ ] **Step 3: Implement** in `src/teamctx/core/select.py`.

Replace the `ContextSelection` dataclass with:
```python
@dataclass(frozen=True)
class ContextSelection:
    """The broker's answer at work-start: rendered cards, the typed certified claims (C),
    honest coverage, and per-proposition closure."""

    cards: tuple[ContextCard, ...]
    claim_cards: tuple[ClaimCard, ...]
    coverage: Coverage
    closure: tuple[ClosureEntry, ...]
```

Replace `select_context` with (derive the claims once; render each to a card; keep both):
```python
def select_context(
    request: RequestContext,
    signals: Iterable[SourceSignal],
    statuses: Iterable[SourceStatus],
) -> ContextSelection:
    """Broker entry point: derive typed claims, render cards, report coverage + closure."""

    coverage = build_coverage(statuses)
    claim_cards = tuple(derive_claims(request, signals))
    cards = tuple(render_collision_claim(claim_card) for claim_card in claim_cards)
    query = no_conflict_query(request)
    closure = (
        ClosureEntry(proposition=query.predicate, status=assess_completeness(query, coverage)),
    )
    return ContextSelection(
        cards=cards,
        claim_cards=claim_cards,
        coverage=coverage,
        closure=closure,
    )
```
(`derive_cards` is unchanged and remains for external callers. The one-line render comprehension also appears there; that minor duplication is acceptable for now.)

- [ ] **Step 4: Run the full gate.**
- `pytest` — all pass. The pre-existing `tests/test_render_selection.py` and `tests/test_work_start_cli.py` must still pass (they read `selection.cards`/`coverage`/`closure`; the new `claim_cards` is additive). If any test constructs `ContextSelection(...)` directly, update that construction to include `claim_cards` (grep: `grep -rn "ContextSelection(" src tests`).
- `ruff check src tests` — clean.
- `mypy src` — Success.

- [ ] **Step 5: Commit**
```bash
git add src/teamctx/core/select.py tests/test_select.py
git commit -m "feat: expose typed certified claims (C) on the broker answer"
```

---

## Task 3: Verify the slice's definition of done

- [ ] **Step 1:** `pytest && ruff check src tests && mypy src` — all green.
- [ ] **Step 2:** Purity guard covers the new module: `pytest tests/test_core_contracts.py::test_core_package_has_no_file_or_runtime_side_effect_imports -q` — pass.
- [ ] **Step 3 (optional live smoke):** `work-start` output is unchanged from slice 2 (this slice adds no CLI/render change):
```bash
GITHUB_TOKEN=$(gh auth token) PYTHONPATH=src python -m teamctx.cli work-start \
  --github-repo ostinato-forge/project-foundry --path docs/foundry-v2-build-plan.md
```
Expected: same collision card + "Coverage complete" as before.

**Definition of done:**
- `evaluate(query, C, κ)` returns `False` by counterexample (a `refutes` card) regardless of closure; `True` only when closure is `complete` and there is no counterexample; `Unknown[reason]` otherwise — the absence-branch gates on `complete`, never on mere absence of a refuting card.
- `ContextSelection.claim_cards` exposes the typed `C`; `evaluate` runs against a real `select_context` output (the three end-to-end tests).
- Full gate green; purity guard covers `evaluate.py`; `work-start` output unchanged.

---

## Notes for the next slice (do not implement here)

Slice 3.5 surfaces the verdict in `work-start`: the CLI (the consumer) computes `evaluate(no_conflict_query(request), selection.claim_cards, selection.closure)` and `render_selection` shows a one-line verdict ("clear / not clear / unknown — absence is not an all-clear"). Keep `evaluate` out of `select.py` to preserve the acyclic import graph (the CLI calls it). The verdict wording is a good thing to settle while dogfooding. `conflicting-evidence` and the existential branch of `evaluate` are implemented but not yet exercised (no `supports`-producing predicate exists until a later card kind); do not fake tests for them.
