# Slice 4 — Projection Boundary + C/H Split + δ Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: superpowers:subagent-driven-development or executing-plans. Checkbox steps.

**Goal:** Lock the last two build-once seams. (a) **C/H split:** a structurally separate, untrusted hint layer `H` on the broker answer (empty today, but the seam exists so it's never retrofitted). (b) **Projection boundary:** selection runs only over the consumer-visible projection (Theorem 5), and the declassification dial `δ` lives on the certificate (default `none`) so the certificate can controlled-declassify rather than be starved.

**Architecture:** `project_visible_signals` is the explicit Δ_P projection (cards derive only from it). `Hint` + `ContextSelection.hints` is the separate `H`. `Coverage` gains `delta: Delta`. δ=count/identity are deferred — there are no invisible-target dangling references to declassify until a later slice introduces reference-target tracking; the field + `none` semantics are what we lock now.

**Tech Stack:** Python 3.12, frozen dataclasses + Literal, pytest, ruff, mypy --strict. All in `core/` (purity-globbed).

---

## File structure
- **Modify `src/teamctx/core/select.py`** — add `Hint`, `Delta`, `project_visible_signals`; `derive_claims` projects first; `Coverage` gains `delta`; `build_coverage` takes `delta`; `ContextSelection` gains `hints`; `select_context` sets `hints=()`.
- **Modify `tests/test_select.py`** — projection (T5) + C/H + δ tests.

---

## Task 0: Branch + plan
- [ ] `git checkout -b build/slice-04-projection-ch-split`
- [ ] `git add docs/superpowers/plans/2026-06-19-slice-04-projection-ch-split.md && git commit -m "docs: slice-04 plan (projection + C/H split + delta)"`

---

## Task 1: C/H split, explicit projection, δ field

**Files:** Modify `src/teamctx/core/select.py`, `tests/test_select.py`.

- [ ] **Step 1: Failing tests.** In `tests/test_select.py` add to the `teamctx.core.select` import group: `Hint`, `build_coverage` (already imported), `project_visible_signals`. The helpers `load_document`, `collision_signal`, `hidden` already exist. Append:
```python
def test_project_visible_signals_drops_invisible_signals() -> None:
    visible = collision_signal()
    invisible = hidden(collision_signal())
    assert project_visible_signals([visible]) == [visible]
    assert project_visible_signals([invisible]) == []


def test_adding_an_invisible_signal_does_not_change_the_observable() -> None:
    # Theorem 5: the observable is invariant under a P-invisible signal.
    document = load_document()
    request = document.request_context
    statuses = document.source_statuses
    visible = collision_signal()
    invisible = hidden(collision_signal())

    base = select_context(request, [visible], statuses)
    perturbed = select_context(request, [visible, invisible], statuses)

    assert base.cards == perturbed.cards
    assert base.claim_cards == perturbed.claim_cards
    assert base.closure == perturbed.closure


def test_selection_has_a_separate_empty_hint_layer() -> None:
    document = load_document()
    selection = select_context(
        document.request_context, document.source_signals, document.source_statuses
    )
    # H is structurally separate from the certified set C; no hint producers yet.
    assert selection.hints == ()


def test_coverage_carries_a_delta_dial_defaulting_to_none() -> None:
    assert build_coverage([]).delta == "none"
```

- [ ] **Step 2: Run** `pytest tests/test_select.py -v` — expect FAIL (`Hint`/`project_visible_signals` import; `Coverage` has no `delta`; `ContextSelection` has no `hints`).

- [ ] **Step 3: Implement** in `src/teamctx/core/select.py`.

Add near the top types (after the imports / before `ClaimCard`, or grouped logically):
```python
Delta = Literal["none", "count", "identity"]


@dataclass(frozen=True)
class Hint:
    """An untrusted, uncertified best-effort guess (the H layer).

    H is **outside the privacy contract**: a hint must be projected to the consumer-visible
    set before it is ever surfaced to a human, and it carries NO certificate weight — it
    never enters the certified card set C. No hint producers exist yet; the layer is kept
    structurally separate so certified and uncertified context never share a channel.
    """

    subject: str
    summary: str
    source: str
```

Add the explicit projection (place it next to `_is_surfaceable`):
```python
def project_visible_signals(signals: Iterable[SourceSignal]) -> list[SourceSignal]:
    """Project signals to the consumer-visible set (Delta_P): drop any the requester may not
    see at all. Selection runs over this projection only, so a P-invisible signal cannot
    affect the observable (Theorem 5: existence-privacy)."""

    return [signal for signal in signals if _is_surfaceable(signal)]
```
Refactor `derive_claims` to project first (selection over the projection only):
```python
def derive_claims(
    request: RequestContext, signals: Iterable[SourceSignal]
) -> list[ClaimCard]:
    """Derive typed claims from the P-visible signals by structural relevance to the request."""

    claims: list[ClaimCard] = []
    for signal in project_visible_signals(signals):
        if signal.signal_type == "collision":
            claim_card = _derive_collision_claim(request, signal)
            if claim_card is not None:
                claims.append(claim_card)
    return claims
```

Add `delta` to `Coverage` (default `none`):
```python
@dataclass(frozen=True)
class Coverage:
    """Honest report of what was checked. Absence of cards is never clearance."""

    entries: tuple[CoverageEntry, ...]
    delta: Delta = "none"
```
Update `build_coverage` to carry `delta`:
```python
def build_coverage(statuses: Iterable[SourceStatus], delta: Delta = "none") -> Coverage:
    """Record each observed source's status verbatim, with the declassification dial. The
    dial defaults to ``none``; ``count``/``identity`` declassification of invisible-target
    dangling references is deferred until reference-target tracking exists."""

    entries = tuple(
        CoverageEntry(
            source_id=status.source_id,
            source_family=status.source_family,
            status=status.status,
            last_checked_at=status.last_checked_at,
        )
        for status in statuses
    )
    return Coverage(entries=entries, delta=delta)
```

Add `hints` to `ContextSelection`:
```python
@dataclass(frozen=True)
class ContextSelection:
    """The broker's answer at work-start: rendered cards, the typed certified claims (C), the
    untrusted hint layer (H), honest coverage, and per-proposition closure."""

    cards: tuple[ContextCard, ...]
    claim_cards: tuple[ClaimCard, ...]
    hints: tuple[Hint, ...]
    coverage: Coverage
    closure: tuple[ClosureEntry, ...]
```
Update `select_context` to set `hints=()`:
```python
    return ContextSelection(
        cards=cards,
        claim_cards=claim_cards,
        hints=(),
        coverage=coverage,
        closure=closure,
    )
```

- [ ] **Step 4: Full gate.** First `grep -rn "ContextSelection(" src tests` — only `select_context` should construct it; if a test constructs it directly, add `hints=()`. Then:
  - `pytest` — all pass (existing `test_hidden_collision_signal_derives_no_claim` still passes; new tests green; `tests/test_render_selection.py` + `tests/test_work_start_cli.py` unaffected — `hints` is additive, `cards`/`coverage`/`closure` unchanged).
  - `ruff check src tests` — clean.
  - `mypy src` — Success.

- [ ] **Step 5: Commit**
```bash
git add src/teamctx/core/select.py tests/test_select.py
git commit -m "feat: lock projection boundary (Delta_P) + C/H split + delta dial on the certificate"
```

---

## Task 2: Verify
- [ ] `pytest && ruff check src tests && mypy src` green.
- [ ] Purity guard: `pytest tests/test_core_contracts.py::test_core_package_has_no_file_or_runtime_side_effect_imports -q`.

**Definition of done:** selection derives only from `project_visible_signals` (P-visible) — a P-invisible signal can't change the observable (T5 test); `ContextSelection.hints` is a separate, empty, untrusted layer; `Coverage.delta` carries the dial at `none`; gate green.

---

## Notes for next slices
δ=count/identity and hint producers arrive with later signal kinds; the seams are now locked so adding them won't reshape the broker answer. Build-once seams #2 (C/H) and #3 (projection) are now in code.
