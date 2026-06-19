# Slice 1 — Typed `claim` + Witness Polarity Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Give the broker's cards a typed proposition (`claim`) with polarity, so a card can be said to witness a query proposition `ρ` or its negation `¬ρ` — the foundation for the consumer `evaluate` SDK and observable soundness (T2) — while keeping `work-start`'s output byte-identical.

**Architecture:** In-place strangler. Introduce a pure typed-proposition layer (`core/prop.py`) *beneath* the existing collision derivation: `derive_claims` produces typed `ClaimCard`s, `render_claim` turns one into the exact same `ContextCard` as today, and `derive_cards` becomes `[render_claim(c) for c in derive_claims(...)]`. The new seam is tested independently; existing output is preserved by construction (the current tests in `tests/test_select.py` already pin it).

**Tech Stack:** Python 3.12, frozen `dataclasses` + `typing.Literal` (no new deps), pydantic contracts (existing), pytest, ruff, mypy --strict.

---

## File structure

- **Create `src/teamctx/core/prop.py`** — the typed-proposition seam. `SubjectRef`, `Prop` (predicate + subject + args, with a registry-derived `shape`), and `witnesses(claim, query)`. Pure: dataclasses + typing only. One responsibility: the proposition algebra. No imports from `core.contracts` (stays a free-standing algebra the SDK will reuse).
- **Modify `src/teamctx/core/select.py`** — add `ClaimCard`, `derive_claims`, `_derive_collision_claim`, `no_conflict_query`, `render_claim`; refactor `derive_cards` to delegate; delete the now-superseded `_derive_collision_card`. This file bridges the proposition algebra (`core.prop`) and the render contract (`core.contracts`).
- **Create `tests/test_prop.py`** — unit tests for the proposition model and `witnesses`.
- **Modify `tests/test_select.py`** — add tests for `derive_claims` (typed claim + polarity) and `render_claim` (reproduces the collision card). Existing `derive_cards`/coverage tests stay and act as the byte-identical guard.

Gates: the core purity test (`tests/test_core_contracts.py::test_core_package_has_no_file_or_runtime_side_effect_imports`) globs `src/teamctx/core/*.py`, so `prop.py` is automatically held to no-I/O. `mypy --strict` and `ruff` cover both new files.

---

## Task 0: Branch and commit the planning docs

**Files:** none (git only). The roadmap doc, `build-plan.md` pointer edit, and this plan are currently uncommitted on `main`.

- [ ] **Step 1: Create the slice branch off `main`**

Run:
```bash
git checkout -b build/slice-01-typed-claim
```
Expected: `Switched to a new branch 'build/slice-01-typed-claim'`

- [ ] **Step 2: Commit the planning docs to keep `main` clean and the branch self-contained**

```bash
git add docs/product/sprints/2026-06-19-milestone-thesis-complete-engine.md \
        docs/engineering/build-plan.md \
        docs/superpowers/plans/2026-06-19-slice-01-typed-claim.md
git commit -m "docs: thesis-complete-engine milestone roadmap + slice-01 plan"
```
Expected: one commit created; `git status` clean.

---

## Task 1: The typed proposition model (`core/prop.py`)

**Files:**
- Create: `src/teamctx/core/prop.py`
- Test: `tests/test_prop.py`

- [ ] **Step 1: Write the failing test**

Create `tests/test_prop.py`:
```python
"""Unit tests for the typed-proposition seam."""

from __future__ import annotations

import pytest

from teamctx.core.prop import Prop, SubjectRef


def test_prop_shape_comes_from_the_predicate_registry() -> None:
    existential = Prop(
        predicate="pr_conflicts_with_path",
        subject=SubjectRef(repo="svc", paths=("a.py",)),
    )
    universal = Prop(
        predicate="no_pr_conflicts_with_paths",
        subject=SubjectRef(repo="svc", paths=("a.py",)),
    )
    assert existential.shape == "existential"
    assert universal.shape == "universal"


def test_unregistered_predicate_is_rejected() -> None:
    bad = Prop(predicate="not_a_real_predicate", subject=SubjectRef(repo="svc"))
    with pytest.raises(ValueError, match="unregistered predicate"):
        _ = bad.shape
```

- [ ] **Step 2: Run test to verify it fails**

Run: `pytest tests/test_prop.py -v`
Expected: FAIL — `ModuleNotFoundError: No module named 'teamctx.core.prop'`

- [ ] **Step 3: Write minimal implementation**

Create `src/teamctx/core/prop.py`:
```python
"""Typed propositions: the broker's claims, with polarity.

A card does not assert free text; it asserts a typed ``Prop`` and *witnesses* it. Whether a
card witnesses a consumer's query proposition ``rho`` or its negation is a deterministic
relation over typed structure (``witnesses``), never a reading of payload. This is the seam
the consumer SDK and observable soundness (Theorem 2) build on.

Pure: dataclasses and typing only — no I/O, time, or randomness (the core purity test
guards this).
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Literal

PropShape = Literal["universal", "existential"]

# The predicates this build models, and their logical shape. A universal ("no PR conflicts
# with any of my paths") is refuted by a single counterexample; an existential ("a PR
# conflicts with this path") is witnessed by a single instance. Card kinds register their
# predicate here as they are added.
PREDICATE_REGISTRY: dict[str, PropShape] = {
    "pr_conflicts_with_path": "existential",
    "no_pr_conflicts_with_paths": "universal",
}


@dataclass(frozen=True)
class SubjectRef:
    """A typed reference to what a proposition is about. For collisions: a repo + paths."""

    repo: str
    paths: tuple[str, ...] = ()


@dataclass(frozen=True)
class Prop:
    """A typed proposition: a registered predicate over a subject, with typed arguments."""

    predicate: str
    subject: SubjectRef
    args: tuple[str, ...] = ()

    @property
    def shape(self) -> PropShape:
        try:
            return PREDICATE_REGISTRY[self.predicate]
        except KeyError as exc:
            raise ValueError(f"unregistered predicate: {self.predicate!r}") from exc
```

- [ ] **Step 4: Run test to verify it passes**

Run: `pytest tests/test_prop.py -v`
Expected: PASS (2 passed)

- [ ] **Step 5: Commit**

```bash
git add src/teamctx/core/prop.py tests/test_prop.py
git commit -m "feat: typed proposition model (Prop, SubjectRef, predicate registry)"
```

---

## Task 2: The witness polarity relation (`witnesses`)

**Files:**
- Modify: `src/teamctx/core/prop.py`
- Test: `tests/test_prop.py`

- [ ] **Step 1: Write the failing test**

Append to `tests/test_prop.py`:
```python
from teamctx.core.prop import witnesses


def test_collision_claim_refutes_the_no_conflict_universal() -> None:
    claim = Prop(
        predicate="pr_conflicts_with_path",
        subject=SubjectRef(repo="svc", paths=("src/auth/token.py",)),
        args=("sig_pr_482_collision",),
    )
    query = Prop(
        predicate="no_pr_conflicts_with_paths",
        subject=SubjectRef(repo="svc", paths=("src/auth/token.py", "src/other.py")),
    )
    # A single existential counterexample refutes the universal — the polarity trap the
    # paper flags (a single-witness "True-only" scheme would mis-handle this universal).
    assert witnesses(claim, query) == "refutes"


def test_claim_over_unrelated_paths_is_not_a_witness() -> None:
    claim = Prop(
        predicate="pr_conflicts_with_path",
        subject=SubjectRef(repo="svc", paths=("src/auth/token.py",)),
    )
    query = Prop(
        predicate="no_pr_conflicts_with_paths",
        subject=SubjectRef(repo="svc", paths=("src/unrelated.py",)),
    )
    assert witnesses(claim, query) == "unrelated"


def test_claim_in_a_different_repo_is_not_a_witness() -> None:
    claim = Prop(
        predicate="pr_conflicts_with_path",
        subject=SubjectRef(repo="svc-a", paths=("src/auth/token.py",)),
    )
    query = Prop(
        predicate="no_pr_conflicts_with_paths",
        subject=SubjectRef(repo="svc-b", paths=("src/auth/token.py",)),
    )
    assert witnesses(claim, query) == "unrelated"
```

- [ ] **Step 2: Run test to verify it fails**

Run: `pytest tests/test_prop.py -v`
Expected: FAIL — `ImportError: cannot import name 'witnesses' from 'teamctx.core.prop'`

- [ ] **Step 3: Write minimal implementation**

Append to `src/teamctx/core/prop.py`:
```python
Witness = Literal["supports", "refutes", "unrelated"]


def witnesses(claim: Prop, query: Prop) -> Witness:
    """Does a card's ``claim`` witness ``query`` (supports), its negation (refutes), or
    neither (unrelated)?

    Deterministic over typed structure only. For this build: an existential
    ``pr_conflicts_with_path`` claim *refutes* the universal ``no_pr_conflicts_with_paths``
    query whenever they share a repo and at least one path — a counterexample to "no
    conflict". ``supports`` is reserved for kinds whose claim establishes a query directly.
    """

    if (
        query.predicate == "no_pr_conflicts_with_paths"
        and claim.predicate == "pr_conflicts_with_path"
        and claim.subject.repo == query.subject.repo
        and bool(set(claim.subject.paths) & set(query.subject.paths))
    ):
        return "refutes"
    return "unrelated"
```

- [ ] **Step 4: Run test to verify it passes**

Run: `pytest tests/test_prop.py -v`
Expected: PASS (5 passed)

- [ ] **Step 5: Commit**

```bash
git add src/teamctx/core/prop.py tests/test_prop.py
git commit -m "feat: witness polarity relation (collision refutes the no-conflict universal)"
```

---

## Task 3: Derive typed claims for collision (`derive_claims`, `ClaimCard`, `no_conflict_query`)

**Files:**
- Modify: `src/teamctx/core/select.py`
- Test: `tests/test_select.py`

- [ ] **Step 1: Write the failing test**

Add to the imports near the top of `tests/test_select.py`:
```python
from teamctx.core.prop import witnesses
from teamctx.core.select import (
    ClaimCard,
    derive_claims,
    no_conflict_query,
)
```

Append this test to `tests/test_select.py`:
```python
def test_collision_derives_a_typed_claim_that_witnesses_the_negation() -> None:
    document = load_document()
    request = document.request_context

    claim_cards = derive_claims(request, [collision_signal()])

    assert len(claim_cards) == 1
    claim_card = claim_cards[0]
    assert isinstance(claim_card, ClaimCard)
    assert claim_card.claim.predicate == "pr_conflicts_with_path"
    assert claim_card.claim.shape == "existential"
    assert claim_card.claim.args == ("sig_pr_482_collision",)
    # the card witnesses NOT "no conflict": a counterexample to the universal query.
    assert witnesses(claim_card.claim, no_conflict_query(request)) == "refutes"


def test_hidden_collision_signal_derives_no_claim() -> None:
    document = load_document()

    claim_cards = derive_claims(document.request_context, [hidden(collision_signal())])

    assert claim_cards == []
```

- [ ] **Step 2: Run test to verify it fails**

Run: `pytest tests/test_select.py -v`
Expected: FAIL — `ImportError: cannot import name 'ClaimCard' from 'teamctx.core.select'`

- [ ] **Step 3: Write minimal implementation**

In `src/teamctx/core/select.py`, add to the imports block:
```python
from teamctx.core.prop import Prop, SubjectRef
```

Add these definitions (place them above `derive_cards`):
```python
@dataclass(frozen=True)
class ClaimCard:
    """A derived typed claim paired with the source signal it was derived from.

    ``claim`` is the proposition the card asserts (and witnesses); ``signal`` carries the
    render inputs. The render card is a pure function of this pair (``render_claim``).
    """

    claim: Prop
    signal: SourceSignal


def no_conflict_query(request: RequestContext) -> Prop:
    """The universal a collision card refutes: 'no open PR conflicts with my paths'."""

    return Prop(
        predicate="no_pr_conflicts_with_paths",
        subject=SubjectRef(repo=request.repo, paths=tuple(request.paths)),
    )


def derive_claims(
    request: RequestContext, signals: Iterable[SourceSignal]
) -> list[ClaimCard]:
    """Derive typed claims from signals by computing structural relevance to the request."""

    claims: list[ClaimCard] = []
    for signal in signals:
        if not _is_surfaceable(signal):
            continue
        if signal.signal_type == "collision":
            claim_card = _derive_collision_claim(request, signal)
            if claim_card is not None:
                claims.append(claim_card)
    return claims


def _derive_collision_claim(
    request: RequestContext, signal: SourceSignal
) -> ClaimCard | None:
    if signal.scope.get("repo") != request.repo:
        return None
    candidate_files = signal.scope.get("files")
    candidate = candidate_files if isinstance(candidate_files, list) else []
    shared = sorted(set(request.paths) & set(candidate))
    if not shared:
        return None
    claim = Prop(
        predicate="pr_conflicts_with_path",
        subject=SubjectRef(repo=request.repo, paths=tuple(shared)),
        args=(signal.id,),
    )
    return ClaimCard(claim=claim, signal=signal)
```

Note: `dataclass` is already imported in `select.py` (used by `Coverage`). `Prop`/`SubjectRef` are the only new imports.

- [ ] **Step 4: Run test to verify it passes**

Run: `pytest tests/test_select.py -v`
Expected: PASS (the two new tests pass; all prior tests still pass — `derive_cards` is untouched so far).

- [ ] **Step 5: Commit**

```bash
git add src/teamctx/core/select.py tests/test_select.py
git commit -m "feat: derive typed collision claims (ClaimCard, derive_claims, no_conflict_query)"
```

---

## Task 4: Render the claim and route `derive_cards` through it (byte-identical)

**Files:**
- Modify: `src/teamctx/core/select.py`
- Test: `tests/test_select.py`

- [ ] **Step 1: Write the failing test**

Add `render_claim` to the `teamctx.core.select` import in `tests/test_select.py`:
```python
from teamctx.core.select import (
    ClaimCard,
    derive_claims,
    no_conflict_query,
    render_claim,
)
```

Append this test to `tests/test_select.py`:
```python
def test_render_claim_reproduces_the_collision_context_card() -> None:
    document = load_document()
    claim_card = derive_claims(document.request_context, [collision_signal()])[0]

    card = render_claim(claim_card)

    # byte-for-byte the same card the pre-typed derivation produced.
    assert card.section == "Needs attention"
    assert card.refs == ["sig_pr_482_collision"]
    assert card.text == "Another open PR changed src/auth/token.py 11 minutes ago."
    assert card.source_display == "GitHub PR #482"
    assert card.freshness == "fresh"
    assert card.confidence == "high"
    assert card.agent_instruction == "verify_before_relying"
    assert card.source_body == "status_only"
    assert "src/auth/token.py" in card.reason
```

- [ ] **Step 2: Run test to verify it fails**

Run: `pytest tests/test_select.py::test_render_claim_reproduces_the_collision_context_card -v`
Expected: FAIL — `ImportError: cannot import name 'render_claim' from 'teamctx.core.select'`

- [ ] **Step 3: Write minimal implementation**

In `src/teamctx/core/select.py`, add `render_claim` (place it directly above `derive_cards`):
```python
def render_claim(claim_card: ClaimCard) -> ContextCard:
    """Render a typed claim into a human-plane ``ContextCard``.

    Pure: the render card is a function of the claim plus its signal. Output matches the
    pre-typed collision derivation byte for byte.
    """

    claim = claim_card.claim
    signal = claim_card.signal
    overlap = ", ".join(claim.subject.paths)
    return ContextCard(
        schema_version="teamctx.context_card.v0",
        id=f"card_{signal.id}",
        section="Needs attention",
        text=signal.evidence_summary,
        why_this_matters=f"you are editing {claim.subject.paths[0]}.",
        source_display=signal.source_display,
        refs=[signal.id],
        reason=f"same repository and file path as the current task: {overlap}",
        scope=signal.scope,
        freshness=signal.freshness,
        confidence=signal.confidence,
        source_body="status_only",
        source_open_target_id=None,
        agent_instruction="verify_before_relying",
    )
```

Now replace the body of `derive_cards` so it delegates, and delete the old `_derive_collision_card`. The new `derive_cards`:
```python
def derive_cards(request: RequestContext, signals: Iterable[SourceSignal]) -> list[ContextCard]:
    """Derive context cards: typed claims (derive_claims) rendered to cards (render_claim)."""

    return [render_claim(claim_card) for claim_card in derive_claims(request, signals)]
```

Delete the entire old `_derive_collision_card` function (its logic now lives in `_derive_collision_claim` + `render_claim`).

- [ ] **Step 4: Run the full suite + lint + types (byte-identical guard)**

Run: `pytest`
Expected: PASS — all tests, including the pre-existing `test_collision_signal_overlapping_request_path_derives_a_card`, `test_only_collision_signals_derive_cards_in_this_vertical`, and `tests/test_render_selection.py::test_render_shows_collision_card_and_honest_incomplete_coverage` (these are the byte-identical guard: `derive_cards` output is unchanged).

Run: `ruff check`
Expected: `All checks passed!`

Run: `mypy src`
Expected: `Success: no issues found`

- [ ] **Step 5: Commit**

```bash
git add src/teamctx/core/select.py tests/test_select.py
git commit -m "refactor: route derive_cards through render_claim over typed claims"
```

---

## Task 5: Verify the slice's definition of done

**Files:** none (verification only).

- [ ] **Step 1: Run the complete gate**

Run:
```bash
pytest && ruff check && mypy src
```
Expected: all tests pass (the 109 prior + the new prop/claim tests), `All checks passed!`, `Success: no issues found`.

- [ ] **Step 2: Confirm the purity guard covers the new module**

Run: `pytest tests/test_core_contracts.py::test_core_package_has_no_file_or_runtime_side_effect_imports -v`
Expected: PASS — confirms `src/teamctx/core/prop.py` introduces no I/O/time/randomness imports.

- [ ] **Step 3: Confirm the live tool still runs unchanged (optional smoke)**

Run:
```bash
GITHUB_TOKEN=$(gh auth token) PYTHONPATH=src python -m teamctx.cli work-start \
  --github-repo ostinato-forge/project-foundry --path docs/foundry-v2-build-plan.md
```
Expected: the same `work-start` output as before this slice (collision card + coverage). This is the dogfood path; output is unchanged because `render_claim` reproduces the card byte-for-byte.

**Definition of done (all must hold):**
- Collision cards are now backed by a typed `claim` (`Prop`) with a registry-derived `shape`.
- `witnesses(claim, no_conflict_query(request)) == "refutes"` — the card correctly witnesses `¬ρ` (the universal polarity trap is covered).
- `work-start` output is byte-identical (guarded by the unchanged `test_select.py` / `test_render_selection.py` assertions).
- Fail-closed machinery preserved: `derive_claims` still gates on `_is_surfaceable`.
- Full gate green; purity guard covers `prop.py`.

---

## Notes for the next slice (do not implement here)

`witnesses` currently returns only `refutes`/`unrelated`. Slice 3 (consumer SDK) generalizes it to `supports` for kinds whose claim establishes a query, and consumes `complete?` (slice 2) for the exhaustive-absence branches. `no_conflict_query` is the first registered query constructor; later kinds add their own. Do not build the predicate algebra out further until a second kind needs it (YAGNI).
