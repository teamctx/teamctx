# Slice 2: `complete?` + `κ.closure` Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Replace the broker's global "all sources fresh" coverage flag with an honest **per-proposition completeness checker** (`assess_completeness`, the paper's `complete?`) plus a per-proposition **closure** carried in the broker's answer (`κ.closure`), so coverage honesty is scoped to *the query's* dependencies, not "all sources."

**Architecture:** A proposition's dependency closure `deps_G` is a small trusted registry of mandated source families per predicate (collision query → `git_hosting`). `assess_completeness(prop, coverage)` reads the per-source coverage and returns `complete` or an `incomplete[reason]`. `select_context` computes this for the work-start query and carries it in `ContextSelection.closure`; the renderer drives its honest-coverage message off the closure instead of the removed `Coverage.complete`.

**Tech Stack:** Python 3.12, frozen dataclasses + `typing.Literal`, pydantic contracts (existing), pytest, ruff, mypy --strict.

---

## Context the implementer needs

- This builds on slice 1. `src/teamctx/core/prop.py` already provides `Prop`, `SubjectRef`, and (in `select.py`) `no_conflict_query(request) -> Prop` returns the universal `Prop(predicate="no_pr_conflicts_with_paths", subject=SubjectRef(repo, paths))`.
- `src/teamctx/core/select.py` currently has: `Coverage` (frozen dataclass, fields `entries: tuple[CoverageEntry, ...]`, plus a `complete` property = "all entries fresh"), `CoverageEntry` (`source_id`, `source_family`, `status`, `last_checked_at`), `build_coverage(statuses)`, `ContextSelection` (`cards`, `coverage`), and `select_context(request, signals, statuses)`.
- The live GitHub path emits one `SourceStatus` with `source_family="git_hosting"`, `status="fresh"` (or `unavailable` when no token). The test fixture `docs/product/discovery/fixtures/contracts/v0/core-contract-document.json` has exactly one status: `source_family="docs"`, `status="stale"`, and **no** `git_hosting` status.
- Because of that, the fixture's collision-query closure is `incomplete[policy-gap]` (the mandated `git_hosting` source is not observed). The live path's closure is `complete` (git_hosting fresh). Both render the **same strings** as today ("Coverage complete..." / "...not an all-clear"), so the existing render test stays green.
- `CoverageEntry.status` is a `str` with values from `fresh|stale|unavailable|blocked|disabled`. "fresh" is the only complete-eligible value.
- The core purity test globs `src/teamctx/core/*.py`; new code in `select.py` must not import os/pathlib/time/etc. (it won't need to).

---

## File structure

- **Modify `src/teamctx/core/select.py`**: add `Completeness`, `ClosureEntry`, `DEPS_REGISTRY`, `deps_for`, `assess_completeness`; add `closure` to `ContextSelection`; compute closure in `select_context`; **remove** the `Coverage.complete` property.
- **Modify `src/teamctx/contract_render.py`**: `render_selection` decides complete-vs-incomplete from `selection.closure` instead of `selection.coverage.complete`.
- **Modify `tests/test_select.py`**: add closure-taxonomy tests; rewrite the coverage tests that asserted the removed `.complete`; update the `select_context` test.

---

## Task 0: Branch and commit the plan

- [ ] **Step 1:** `git checkout -b build/slice-02-complete-closure`
- [ ] **Step 2:**
```bash
git add docs/superpowers/plans/2026-06-19-slice-02-complete-closure.md
git commit -m "docs: slice-02 plan (per-proposition complete? + kappa.closure)"
```

---

## Task 1: Closure taxonomy + `deps_for` + `assess_completeness`

**Files:** Modify `src/teamctx/core/select.py`; Test `tests/test_select.py`.

- [ ] **Step 1: Write the failing tests**

In the **top import block** of `tests/test_select.py`, ensure these imports exist (add what's missing, keep import order ruff-`I`-clean): `import pytest`; `from teamctx.core.contracts import SourceStatus`; `from teamctx.core.prop import Prop, SubjectRef` (slice 1 already imports `witnesses`); and add `assess_completeness`, `deps_for` to the `from teamctx.core.select import (...)` group (alphabetized). Then append these helpers and tests to the end of the file:
```python
def _git_hosting_status(status: str) -> SourceStatus:
    """A git_hosting SourceStatus for closure tests (derived from the fixture's status)."""
    base = load_document().source_statuses[0]
    return base.model_copy(
        update={"source_id": "github_pr_metadata", "source_family": "git_hosting", "status": status}
    )


def _collision_query() -> Prop:
    return Prop(
        predicate="no_pr_conflicts_with_paths",
        subject=SubjectRef(repo="auth-service", paths=("src/auth/token.py",)),
    )


def test_deps_for_collision_query_is_git_hosting() -> None:
    assert deps_for(_collision_query()) == frozenset({"git_hosting"})


def test_deps_for_unregistered_predicate_raises() -> None:
    with pytest.raises(ValueError, match="no dependency closure registered"):
        deps_for(Prop(predicate="some_unmodeled_predicate", subject=SubjectRef(repo="r")))


def test_closure_complete_when_git_hosting_fresh() -> None:
    coverage = build_coverage([_git_hosting_status("fresh")])
    assert assess_completeness(_collision_query(), coverage) == "complete"


def test_closure_stale_dep_when_git_hosting_not_fresh() -> None:
    coverage = build_coverage([_git_hosting_status("stale")])
    assert assess_completeness(_collision_query(), coverage) == "incomplete[stale-dep]"


def test_closure_policy_gap_when_git_hosting_unobserved() -> None:
    # the fixture has only a docs source, the mandated git_hosting source is absent.
    coverage = build_coverage(load_document().source_statuses)
    assert assess_completeness(_collision_query(), coverage) == "incomplete[policy-gap]"


def test_closure_policy_gap_when_no_sources_checked() -> None:
    assert assess_completeness(_collision_query(), build_coverage([])) == "incomplete[policy-gap]"
```

- [ ] **Step 2: Run** `pytest tests/test_select.py -v`, expect FAIL: `cannot import name 'assess_completeness'`.

- [ ] **Step 3: Implement.** In `src/teamctx/core/select.py`:

Add to the typing import: `from typing import Literal` (if not present). Then add these near the `Coverage` definitions:
```python
Completeness = Literal[
    "complete",
    "incomplete[dangling]",
    "incomplete[stale-dep]",
    "incomplete[policy-gap]",
    "incomplete[unbounded]",
    "incomplete[unmodeled-ref]",
]

# deps_G: the trusted, mandated source families a proposition's truth depends on. A
# predicate is registered here as its card kind is added. An unregistered predicate fails
# loud: we never silently certify a query whose dependencies we have not modeled.
DEPS_REGISTRY: dict[str, frozenset[str]] = {
    "no_pr_conflicts_with_paths": frozenset({"git_hosting"}),
}


def deps_for(prop: Prop) -> frozenset[str]:
    """The mandated source families whose state can affect ``prop`` (deps_G)."""

    try:
        return DEPS_REGISTRY[prop.predicate]
    except KeyError as exc:
        raise ValueError(
            f"no dependency closure registered for predicate {prop.predicate!r}"
        ) from exc


def assess_completeness(prop: Prop, coverage: Coverage) -> Completeness:
    """The paper's ``complete?``: is every mandated dependency of ``prop`` observed fresh?

    Returns ``incomplete[policy-gap]`` if a mandated source family is absent from coverage,
    ``incomplete[stale-dep]`` if present but not fresh, else ``complete``. The reasons
    ``dangling``/``unbounded``/``unmodeled-ref`` are defined but not yet emitted (they need
    reference-target / connector-schema structure introduced in later slices).
    """

    entries_by_family: dict[str, list[CoverageEntry]] = {}
    for entry in coverage.entries:
        entries_by_family.setdefault(entry.source_family, []).append(entry)

    stale_seen = False
    for family in sorted(deps_for(prop)):
        family_entries = entries_by_family.get(family, [])
        if not family_entries:
            return "incomplete[policy-gap]"
        if any(entry.status != "fresh" for entry in family_entries):
            stale_seen = True
    if stale_seen:
        return "incomplete[stale-dep]"
    return "complete"
```
`deps_for` and `assess_completeness` need `Prop` imported in `select.py` (slice 1 already added `from teamctx.core.prop import Prop, SubjectRef`). Confirm that import exists.

- [ ] **Step 4: Run** `pytest tests/test_select.py -v`, expect PASS (new tests green; existing tests still pass, nothing removed yet).

- [ ] **Step 5: Commit**
```bash
git add src/teamctx/core/select.py tests/test_select.py
git commit -m "feat: per-proposition completeness (deps_for + assess_completeness)"
```

---

## Task 2: Carry `closure` in the answer, render off it, remove `Coverage.complete`

**Files:** Modify `src/teamctx/core/select.py`, `src/teamctx/contract_render.py`, `tests/test_select.py`.

- [ ] **Step 1: Write/adjust the failing tests** in `tests/test_select.py`.

Add `ClosureEntry` and `no_conflict_query` to the `teamctx.core.select` import group (alphabetized). Append:
```python
def test_select_context_carries_the_collision_query_closure() -> None:
    document = load_document()

    selection = select_context(
        document.request_context, document.source_signals, document.source_statuses
    )

    # cards are derived, and the answer carries the collision query's closure.
    assert [card.refs[0] for card in selection.cards] == ["sig_pr_482_collision"]
    assert len(selection.closure) == 1
    entry = selection.closure[0]
    assert entry.proposition == "no_pr_conflicts_with_paths"
    # the fixture observes no git_hosting source -> the collision query is policy-gapped.
    assert entry.status == "incomplete[policy-gap]"
```

Now REWRITE the three existing coverage tests that referenced the removed `Coverage.complete`. Replace `test_a_stale_source_makes_coverage_incomplete_and_is_reported`, `test_no_checked_sources_is_not_complete_coverage`, and `test_all_fresh_sources_make_coverage_complete` with:
```python
def test_coverage_reports_each_checked_source_status() -> None:
    # per-source health is still surfaced (absence of cards is never clearance).
    coverage = build_coverage(load_document().source_statuses)
    assert any(entry.status == "stale" for entry in coverage.entries)


def test_collision_closure_is_complete_only_when_git_hosting_is_fresh() -> None:
    fresh = assess_completeness(_collision_query(), build_coverage([_git_hosting_status("fresh")]))
    stale = assess_completeness(_collision_query(), build_coverage([_git_hosting_status("stale")]))
    assert fresh == "complete"
    assert stale == "incomplete[stale-dep]"
```
And update `test_select_context_returns_derived_cards_and_coverage_together`: it currently asserts `selection.coverage.complete is False`. Remove that assertion (the new `test_select_context_carries_the_collision_query_closure` covers closure); keep the card assertion, or delete this now-redundant test if its card assertion duplicates the new one. (Delete it, the new closure test asserts the same cards.)

- [ ] **Step 2: Run** `pytest tests/test_select.py -v`, expect FAIL: `ClosureEntry` import error and/or `ContextSelection` has no `closure`.

- [ ] **Step 3: Implement.**

In `src/teamctx/core/select.py`:

Add the `ClosureEntry` dataclass near `Coverage`:
```python
@dataclass(frozen=True)
class ClosureEntry:
    """A per-proposition completeness status for the coverage certificate (kappa.closure)."""

    proposition: str
    status: Completeness
```

Extend `ContextSelection` with a `closure` field:
```python
@dataclass(frozen=True)
class ContextSelection:
    """The broker's answer at work-start: derived cards, honest coverage, and per-
    proposition closure."""

    cards: tuple[ContextCard, ...]
    coverage: Coverage
    closure: tuple[ClosureEntry, ...]
```

Update `select_context` to compute and carry the closure:
```python
def select_context(
    request: RequestContext,
    signals: Iterable[SourceSignal],
    statuses: Iterable[SourceStatus],
) -> ContextSelection:
    """Broker entry point: derive cards, report coverage, and assess per-proposition closure."""

    coverage = build_coverage(statuses)
    query = no_conflict_query(request)
    closure = (
        ClosureEntry(proposition=query.predicate, status=assess_completeness(query, coverage)),
    )
    return ContextSelection(
        cards=tuple(derive_cards(request, signals)),
        coverage=coverage,
        closure=closure,
    )
```

**Remove** the `complete` property from `Coverage` (the whole `@property def complete` block).

In `src/teamctx/contract_render.py`, in `render_selection`, replace the `if coverage.complete:` decision with a closure-driven one. Change:
```python
    if coverage.complete:
        lines.append("Coverage complete across checked sources.")
    else:
        lines.append(
            "Absence of a card is not an all-clear; "
            "treat unobserved or stale sources as Unknown."
        )
```
to:
```python
    complete = bool(selection.closure) and all(
        entry.status == "complete" for entry in selection.closure
    )
    if complete:
        lines.append("Coverage complete across checked sources.")
    else:
        lines.append(
            "Absence of a card is not an all-clear; "
            "treat unobserved or stale sources as Unknown."
        )
```
(The per-source entry listing above it is unchanged, it still iterates `coverage.entries`.)

- [ ] **Step 4: Run the full gate.**
- `pytest`, all pass. The pre-existing `tests/test_render_selection.py::test_render_shows_collision_card_and_honest_incomplete_coverage` must STILL pass unchanged (fixture closure is policy-gap → "not an all-clear" string present).
- `ruff check src tests`, clean.
- `mypy src`, Success.

- [ ] **Step 5: Commit**
```bash
git add src/teamctx/core/select.py src/teamctx/contract_render.py tests/test_select.py
git commit -m "feat: carry kappa.closure in the answer; render off it; drop global Coverage.complete"
```

---

## Task 3: Verify the slice's definition of done

- [ ] **Step 1:** `pytest && ruff check src tests && mypy src`, all green.
- [ ] **Step 2:** Purity guard: `pytest tests/test_core_contracts.py::test_core_package_has_no_file_or_runtime_side_effect_imports -q`, pass.
- [ ] **Step 3 (optional live smoke):**
```bash
GITHUB_TOKEN=$(gh auth token) PYTHONPATH=src python -m teamctx.cli work-start \
  --github-repo ostinato-forge/project-foundry --path docs/foundry-v2-build-plan.md
```
Expected: collision card + "Coverage complete across checked sources." (git_hosting fresh → closure complete). Output text unchanged from slice 1.

**Definition of done:**
- `assess_completeness` returns `complete` only when the collision query's mandated `git_hosting` dep is observed fresh; `incomplete[stale-dep]` when present-not-fresh; `incomplete[policy-gap]` when absent.
- `deps_for` raises on an unregistered predicate.
- The answer carries `ContextSelection.closure`; the renderer drives complete-vs-incomplete off it; `Coverage.complete` is gone.
- Render output for the live path and the fixture is unchanged (same strings); only the underlying reasoning is now per-proposition.
- Full gate green; purity guard covers the core.

---

## Notes for the next slice (do not implement here)

Slice 3 (`evaluate`) consumes this: `⟦ρ⟧⁻ = False` if a card witnesses `¬ρ` (a `refutes` from slice 1); else `True` only if `assess_completeness(ρ) == "complete"` and no `refutes`; else `Unknown[reason]` carrying the `incomplete[...]` tag. The absence-branch (`True`) MUST gate on `complete`, never on the mere absence of a `refutes`. `ClosureEntry.proposition` will need to become a stable per-query id (not just the predicate) once there are multiple queries per request.
