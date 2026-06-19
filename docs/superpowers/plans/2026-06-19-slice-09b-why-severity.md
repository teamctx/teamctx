# Slice 9b — Structured `why` (#11) + Severity Decomposition (#6)

> REQUIRED SUB-SKILL: superpowers:subagent-driven-development. Checkbox steps.

**Goal:** Make cards machine-auditable and conformance-comparable. (#11) Each card carries a machine-readable `reason_code` alongside its prose. (#6) Each card carries a **severity decomposition** (`value`, `kind_base`, `magnitude_norm`, `scope_mult`) computed deterministically, with a **conformance golden** so any conforming broker produces identical numbers. Severity *calibration* (the default constants) stays deferred — this locks the structure + determinism, not the tuned values.

**Architecture:** A `Severity` model on the card; `core/severity.py` computes `severity = clamp01(kind_base × (1 + α·magnitude_norm) × scope_mult)` per card predicate (pure). `reason_code` + `severity` are **optional** fields on `ContextCard` (defaults), so the legacy connector path and fixtures are unaffected; the four `render_*_claim` functions populate them.

**Tech Stack:** Python 3.12, pydantic, frozen dataclasses, pytest, ruff, mypy --strict. `severity.py` in `core/` (pure).

---

## File structure
- `src/teamctx/core/contracts.py` — `Severity` model; `ContextCard` gains `reason_code: str = ""`, `severity: Severity | None = None`.
- `src/teamctx/core/severity.py` (new, pure) — `KIND_BASE`, `ALPHA`, `compute_severity(card_predicate, claim) -> Severity`.
- `src/teamctx/core/select.py` — the four render fns set `reason_code` + `severity`.
- `tests/test_severity.py` — conformance golden.
- `tests/test_select.py` — render fns populate reason_code/severity.

---

## Task 0: Branch + plan
- [ ] `cd /home/eparenti/agents/repos/teamctx && git checkout -b build/slice-09b-why-severity`
- [ ] `git add docs/superpowers/plans/2026-06-19-slice-09b-why-severity.md && git commit -m "docs: slice-09b plan (structured why + severity decomposition)"`

---

## Task 1: Severity model + `compute_severity` + conformance golden

**Files:** `contracts.py`, create `core/severity.py`, create `tests/test_severity.py`.

- [ ] **Step 1: Failing test.** Create `tests/test_severity.py`:
```python
"""Severity decomposition is deterministic and conformance-comparable (calibration deferred)."""

from __future__ import annotations

from teamctx.core.prop import Prop, SubjectRef
from teamctx.core.severity import compute_severity


def _claim(predicate: str, paths: tuple[str, ...]) -> Prop:
    return Prop(predicate=predicate, subject=SubjectRef(repo="r", paths=paths))


def test_collision_severity_conformance_golden() -> None:
    sev = compute_severity("pr_conflicts_with_path", _claim("pr_conflicts_with_path", ("a.py",)))
    # kind_base 0.8, magnitude_norm = 1/5 = 0.2, scope_mult 1.0
    # value = clamp01(0.8 * (1 + 0.5*0.2) * 1.0) = 0.88
    assert sev.kind_base == 0.8
    assert sev.magnitude_norm == 0.2
    assert sev.scope_mult == 1.0
    assert sev.value == 0.88


def test_severity_value_is_clamped_to_one() -> None:
    # five overlapping paths -> magnitude_norm clamps at 1.0; high kind_base stays <= 1.
    sev = compute_severity(
        "pr_conflicts_with_path",
        _claim("pr_conflicts_with_path", ("a", "b", "c", "d", "e", "f")),
    )
    assert sev.magnitude_norm == 1.0
    assert 0.0 <= sev.value <= 1.0


def test_each_kind_has_a_registered_base() -> None:
    from teamctx.core.severity import KIND_BASE

    for predicate in (
        "pr_conflicts_with_path",
        "issue_criteria_changed",
        "doc_superseded",
        "gate_failed",
    ):
        assert predicate in KIND_BASE


def test_unregistered_predicate_severity_raises() -> None:
    import pytest

    with pytest.raises(ValueError, match="no severity base"):
        compute_severity("nope", _claim("pr_conflicts_with_path", ("a.py",)))
```

- [ ] **Step 2: Run** `pytest tests/test_severity.py -v` — FAIL (module missing).

- [ ] **Step 3: Implement.**

In `src/teamctx/core/contracts.py`, add (near `ContextCard`):
```python
class Severity(ContractModel):
    """Severity decomposition (kept for audit; the value is clamp01(kind_base ×
    (1 + alpha·magnitude_norm) × scope_mult)). Calibration of the constants is deferred."""

    value: float
    kind_base: float
    magnitude_norm: float
    scope_mult: float
```
And add two optional fields to `ContextCard` (so legacy/fixture constructions are unaffected):
```python
    reason_code: str = ""
    severity: Severity | None = None
```
(Place them among the existing `ContextCard` fields; both have defaults so they go after required fields.)

Create `src/teamctx/core/severity.py`:
```python
"""Deterministic severity decomposition for cards (calibration deferred).

severity = clamp01(kind_base × (1 + ALPHA·magnitude_norm) × scope_mult). The decomposition
is retained on the card for audit and conformance: any conforming broker computes identical
numbers for identical inputs. The constants are placeholder defaults — calibration needs
deployment telemetry (out of scope here). Pure: no I/O.
"""

from __future__ import annotations

from teamctx.core.contracts import Severity
from teamctx.core.prop import Prop

# Placeholder bases per card predicate (cost-of-not-knowing). Calibration deferred.
KIND_BASE: dict[str, float] = {
    "pr_conflicts_with_path": 0.8,
    "issue_criteria_changed": 0.5,
    "doc_superseded": 0.4,
    "gate_failed": 0.7,
}
ALPHA = 0.5
_MAGNITUDE_NORM_DIVISOR = 5.0


def compute_severity(card_predicate: str, claim: Prop) -> Severity:
    """Compute the severity decomposition for a card. Magnitude is the fan-out (number of
    subject items), normalized and clamped to [0, 1]; scope_mult is 1.0 for now."""

    try:
        kind_base = KIND_BASE[card_predicate]
    except KeyError as exc:
        raise ValueError(f"no severity base registered for predicate {card_predicate!r}") from exc

    magnitude_norm = round(min(1.0, len(claim.subject.paths) / _MAGNITUDE_NORM_DIVISOR), 4)
    scope_mult = 1.0
    value = round(min(1.0, kind_base * (1 + ALPHA * magnitude_norm) * scope_mult), 4)
    return Severity(
        value=value, kind_base=kind_base, magnitude_norm=magnitude_norm, scope_mult=scope_mult
    )
```

- [ ] **Step 4:** `pytest tests/test_severity.py -v` PASS; `ruff check src tests`; `mypy src` clean; purity guard passes (covers `severity.py` — only imports contracts/prop, no I/O).

- [ ] **Step 5: Commit**
```bash
git add src/teamctx/core/contracts.py src/teamctx/core/severity.py tests/test_severity.py
git commit -m "feat: severity decomposition + conformance golden (calibration deferred)"
```

---

## Task 2: Render fns set `reason_code` + `severity`

**Files:** `src/teamctx/core/select.py`, `tests/test_select.py`.

- [ ] **Step 1: Failing test.** Append to `tests/test_select.py`:
```python
def test_collision_card_has_reason_code_and_severity() -> None:
    document = load_document()
    selection = select_context(
        document.request_context, document.source_signals, document.source_statuses
    )
    card = selection.cards[0]
    assert card.reason_code == "collision.same_path"
    assert card.severity is not None
    assert card.severity.kind_base == 0.8
```

- [ ] **Step 2: Run** `pytest tests/test_select.py -v` — FAIL (reason_code empty / severity None).

- [ ] **Step 3: Implement** in `src/teamctx/core/select.py`. Import: `from teamctx.core.severity import compute_severity`. In each `render_*_claim`, add `reason_code=...` and `severity=compute_severity(claim.predicate, claim)` to the `ContextCard(...)` construction:
  - `render_collision_claim`: `reason_code="collision.same_path"`
  - `render_criteria_changed_claim`: `reason_code="criteria.changed"`
  - `render_doc_superseded_claim`: `reason_code="doc.superseded"`
  - `render_missed_gate_claim`: `reason_code="gate.failed"`
  Each adds (alongside the existing fields): `reason_code="<the code>"`, `severity=compute_severity(claim.predicate, claim)`.

- [ ] **Step 4: Full gate.** `pytest` — all pass (the byte-identical-era collision tests assert specific fields like text/refs/reason; reason_code/severity are NEW additive fields, so those assertions still hold; the live integration/render tests don't assert reason_code/severity). `ruff check src tests`; `mypy src`. If any existing test asserted the FULL set of card fields via equality (unlikely — they assert individual fields), generalize; report it.

- [ ] **Step 5: Commit**
```bash
git add src/teamctx/core/select.py tests/test_select.py
git commit -m "feat: cards carry a structured reason_code + severity decomposition"
```

---

## Task 3: Verify
- [ ] `pytest && ruff check src tests && mypy src` green; purity guard passes.
- [ ] Optional live smoke: `work-start` output is unchanged in PROSE (reason_code/severity are structured fields, not rendered text — the human plane still shows the same lines). They're available on the card objects for machine/audit use.

**Definition of done:** `compute_severity` is deterministic with a conformance golden; cards carry `reason_code` (machine-readable) + `severity` decomposition; legacy/fixture card construction unaffected (optional fields); gate green. This + 9a completes the engine's explainability/replay finish-line. **The thesis-complete engine milestone is done.**

## Notes
The render layer still shows prose; a later slice could derive the prose `reason` FROM `reason_code`+params (fully structured why) and add the dogfood's "to see the change, open <source>" legibility. Severity is not yet used for ranking/Route — that's a product-surface concern, deferred.
