# Slice 5: Registry-Driven Multi-Kind Engine Implementation Plan

> REQUIRED SUB-SKILL: superpowers:subagent-driven-development. Checkbox steps.

**Goal:** Generalize the broker from a single hardcoded collision kind to a **registry of card kinds**, so new kinds (criteria-changed, doc-superseded, missed-gate) are added by registering an entry, not by editing the engine's control flow. **Behavior-preserving:** collision stays the only registered kind, so `work-start` output and all existing tests are unchanged. Also add the `witnesses` property test the slice-1 review asked for.

**Architecture:** `witnesses` becomes driven by a `REFUTES_PAIRS` set of `(card_predicate, query_predicate)`. `select.py` gets a `CardKind` registry (`CARD_KINDS`) of `{signal_type, card_predicate, derive, query, render}`; `derive_claims` dispatches by `signal_type`, rendering dispatches by `card_predicate`, and `select_context` computes one closure entry per registered kind's query. With only collision registered, every output is identical to today.

**Tech Stack:** Python 3.12, frozen dataclasses, `typing.Callable`/`Literal`, pytest, ruff, mypy --strict.

---

## File structure
- **Modify `src/teamctx/core/prop.py`**: `REFUTES_PAIRS` registry; `witnesses` reads it.
- **Modify `src/teamctx/core/select.py`**: `CardKind` dataclass + `CARD_KINDS` registry; `derive_claims` + render dispatch via registry; `select_context` closure-per-kind.
- **Modify `tests/test_prop.py`**: property test over `REFUTES_PAIRS`.
- **Modify `tests/test_select.py`**: registry-dispatch test (still collision-only).

---

## Task 0: Branch + plan
- [ ] `cd /home/eparenti/agents/repos/teamctx && git checkout -b build/slice-05-multikind-engine`
- [ ] `git add docs/superpowers/plans/2026-06-19-slice-05-multikind-engine.md && git commit -m "docs: slice-05 plan (registry-driven multi-kind engine)"`

---

## Task 1: Registry-driven `witnesses` + property test

**Files:** `src/teamctx/core/prop.py`, `tests/test_prop.py`.

- [ ] **Step 1: Failing test.** Append to `tests/test_prop.py`:
```python
from teamctx.core.prop import REFUTES_PAIRS


def test_every_refutes_pair_is_registered_and_distinct() -> None:
    # each pair is (card_predicate, query_predicate); both must be in the shape registry,
    # and a card predicate never equals the query predicate it refutes.
    from teamctx.core.prop import PREDICATE_REGISTRY

    for card_pred, query_pred in REFUTES_PAIRS:
        assert card_pred in PREDICATE_REGISTRY
        assert query_pred in PREDICATE_REGISTRY
        assert card_pred != query_pred


def test_witnesses_is_total_and_never_double_witnesses() -> None:
    # totality: witnesses returns a valid verdict for any registered pair; and no claim
    # both supports and refutes the same query (no pair appears as both directions).
    for card_pred, query_pred in REFUTES_PAIRS:
        assert (query_pred, card_pred) not in REFUTES_PAIRS
```

- [ ] **Step 2: Run** `pytest tests/test_prop.py -v`, FAIL (`REFUTES_PAIRS` import).

- [ ] **Step 3: Implement** in `src/teamctx/core/prop.py`. Replace the hardcoded `witnesses` body with a registry-driven one, and add the registry above it:
```python
# Each pair is (card_predicate, query_predicate): a card asserting card_predicate REFUTES
# the universal query_predicate when they share a repo and at least one subject item. Card
# kinds register their pair here as they are added.
REFUTES_PAIRS: frozenset[tuple[str, str]] = frozenset(
    {
        ("pr_conflicts_with_path", "no_pr_conflicts_with_paths"),
    }
)


def witnesses(claim: Prop, query: Prop) -> Witness:
    """Does a card's ``claim`` witness ``query`` (supports), its negation (refutes), or
    neither (unrelated)? Deterministic over typed structure only.

    A registered ``(claim.predicate, query.predicate)`` refutes-pair, with a shared repo and
    overlapping subject items, refutes the (universal) query, a counterexample. ``supports``
    is reserved for kinds whose claim establishes a query directly.
    """

    if (
        (claim.predicate, query.predicate) in REFUTES_PAIRS
        and claim.subject.repo == query.subject.repo
        and set(claim.subject.paths) & set(query.subject.paths)
    ):
        return "refutes"
    return "unrelated"
```
(Keep `Witness` defined as it is. The collision pair's behavior is identical to before.)

- [ ] **Step 4: Run** `pytest tests/test_prop.py -v`, PASS (all, including the prior witness tests, collision behavior unchanged). `ruff check src tests`, `mypy src` clean.

- [ ] **Step 5: Commit**
```bash
git add src/teamctx/core/prop.py tests/test_prop.py
git commit -m "refactor: registry-driven witnesses (REFUTES_PAIRS) + property test"
```

---

## Task 2: `CardKind` registry in the broker (behavior-preserving)

**Files:** `src/teamctx/core/select.py`, `tests/test_select.py`.

- [ ] **Step 1: Failing test.** In `tests/test_select.py` add `CARD_KINDS` and `CardKind` to the `teamctx.core.select` import group. Append:
```python
def test_card_kinds_registry_has_collision() -> None:
    signal_types = {kind.signal_type for kind in CARD_KINDS}
    assert "collision" in signal_types


def test_select_context_still_derives_only_collision_in_this_registry() -> None:
    document = load_document()
    selection = select_context(
        document.request_context, document.source_signals, document.source_statuses
    )
    # registry currently has only the collision kind -> behavior unchanged.
    assert [c.refs[0] for c in selection.cards] == ["sig_pr_482_collision"]
    assert [e.proposition for e in selection.closure] == ["no_pr_conflicts_with_paths"]
```

- [ ] **Step 2: Run** `pytest tests/test_select.py -v`, FAIL (`CardKind`/`CARD_KINDS` import).

- [ ] **Step 3: Implement** in `src/teamctx/core/select.py`.

Add `Callable` to the imports: `from collections.abc import Callable, Iterable`.

Define `CardKind` and the registry AFTER `_derive_collision_claim`, `no_conflict_query`, and `render_collision_claim` are defined (they're referenced by the registry). Place this block after `render_collision_claim`:
```python
@dataclass(frozen=True)
class CardKind:
    """One registered card kind: how to derive it, what universal it refutes, how to render
    it. New kinds are added by appending an entry, the engine's control flow is unchanged."""

    signal_type: str
    card_predicate: str
    derive: Callable[[RequestContext, SourceSignal], "ClaimCard | None"]
    query: Callable[[RequestContext], Prop]
    render: Callable[["ClaimCard"], ContextCard]


CARD_KINDS: tuple[CardKind, ...] = (
    CardKind(
        signal_type="collision",
        card_predicate="pr_conflicts_with_path",
        derive=_derive_collision_claim,
        query=no_conflict_query,
        render=render_collision_claim,
    ),
)

_KIND_BY_SIGNAL_TYPE: dict[str, CardKind] = {kind.signal_type: kind for kind in CARD_KINDS}
_RENDER_BY_PREDICATE: dict[str, Callable[["ClaimCard"], ContextCard]] = {
    kind.card_predicate: kind.render for kind in CARD_KINDS
}


def render_claim(claim_card: ClaimCard) -> ContextCard:
    """Render a claim card via its kind's renderer (dispatch on the card predicate)."""

    return _RENDER_BY_PREDICATE[claim_card.claim.predicate](claim_card)
```

Replace `derive_claims` to dispatch via the registry:
```python
def derive_claims(
    request: RequestContext, signals: Iterable[SourceSignal]
) -> list[ClaimCard]:
    """Derive typed claims from the P-visible signals, dispatching by registered card kind."""

    claims: list[ClaimCard] = []
    for signal in project_visible_signals(signals):
        kind = _KIND_BY_SIGNAL_TYPE.get(signal.signal_type)
        if kind is None:
            continue
        claim_card = kind.derive(request, signal)
        if claim_card is not None:
            claims.append(claim_card)
    return claims
```

Replace `select_context` to render via `render_claim` and compute one closure entry per registered kind:
```python
def select_context(
    request: RequestContext,
    signals: Iterable[SourceSignal],
    statuses: Iterable[SourceStatus],
) -> ContextSelection:
    """Broker entry point: derive typed claims, render cards, report coverage + per-kind closure."""

    coverage = build_coverage(statuses)
    claim_cards = tuple(derive_claims(request, signals))
    cards = tuple(render_claim(claim_card) for claim_card in claim_cards)
    closure = tuple(
        ClosureEntry(
            proposition=kind.query(request).predicate,
            status=assess_completeness(kind.query(request), coverage),
        )
        for kind in CARD_KINDS
    )
    return ContextSelection(
        cards=cards,
        claim_cards=claim_cards,
        hints=(),
        coverage=coverage,
        closure=closure,
    )
```
Keep `derive_cards` working (it calls `derive_claims` + a renderer). Update it to use `render_claim`:
```python
def derive_cards(request: RequestContext, signals: Iterable[SourceSignal]) -> list[ContextCard]:
    """Derive context cards: typed claims rendered via their kind's renderer."""

    return [render_claim(claim_card) for claim_card in derive_claims(request, signals)]
```

- [ ] **Step 4: Full gate.**
- `pytest`, ALL pass. Existing collision/render/CLI/integration/evaluate tests must be unchanged-green (only collision is registered → identical behavior). Note: `no_conflict_query` is still used (by the registry); `render_collision_claim` still used (by the registry).
- `ruff check src tests`, clean.
- `mypy src`, Success (the `Callable` forward-ref strings to `ClaimCard` resolve since `from __future__ import annotations` is active; if mypy objects, drop the quotes since `ClaimCard` is defined above the registry).

- [ ] **Step 5: Commit**
```bash
git add src/teamctx/core/select.py tests/test_select.py
git commit -m "refactor: registry-driven card kinds (CARD_KINDS); collision-only, behavior-preserving"
```

---

## Task 3: Verify
- [ ] `pytest && ruff check src tests && mypy src` green.
- [ ] Purity guard passes.
- [ ] Live smoke unchanged: `GITHUB_TOKEN=$(gh auth token) PYTHONPATH=src python -m teamctx.cli work-start --github-repo ostinato-forge/project-foundry --path docs/foundry-v2-build-plan.md`, same collision card + NOT CLEAR verdict as before.

**Definition of done:** engine is registry-driven (`REFUTES_PAIRS`, `CARD_KINDS`); collision is the only registered kind so all behavior/output is identical; `witnesses` property test added; gate green. Adding a kind is now: append to `CARD_KINDS` + `REFUTES_PAIRS` + the predicate/deps registries + a derive/render fn + a signal type + a fixture.

## Notes for next slices
Slices 6–7 add kinds by registration only. Each new kind needs: a `SignalType` literal value in `contracts.py`, a `_derive_<kind>_claim`, a `<kind>_query` constructor, `PREDICATE_REGISTRY` shapes for both predicates, a `REFUTES_PAIRS` entry, a `DEPS_REGISTRY` entry for the query predicate, a `render_<kind>_claim`, a `CARD_KINDS` entry, and fixture signals. Multi-kind closure + multi-verdict rendering will then light up; the CLI verdict line (slice 3.5) currently shows the collision verdict, when a 2nd kind lands, decide whether to render all verdicts (likely yes: loop `selection.closure`/per-kind `evaluate`).
