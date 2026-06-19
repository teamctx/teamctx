# Slice 8a — Thin Authority: Core Logic + Broker Integration

> REQUIRED SUB-SKILL: superpowers:subagent-driven-development. Checkbox steps.

**Goal:** Pillar **S2** — separate evidence from authority. Add the core authority logic: from governance **declarations**, compute a per-subject authority state — **resolved / conflicted / missing / unknown[stale-authority]** — that **refuses to adjudicate** a conflict (surfaces it, never picks) and **never lets a fresh lower-priority source override a stale higher-priority one**. Carry it on the broker answer (`κ.authority`). Pure core only — the `.teamctx` file loader + CLI/render is slice 8b.

**Architecture:** `core/authority.py` (pure): `AuthorityDecl` (a declaration), `assess_authority(subject, declarations) -> AuthorityEntry`. Declarations are assumed already projected to the consumer-visible set Δ_P (the loader in 8b filters by `can_read`; authority over invisible sources contributes nothing — preserves T5). `select_context` gains a `declarations` param (default `()`) and computes `ContextSelection.authority`.

**Tech Stack:** Python 3.12, frozen dataclasses, Literal, pytest, ruff, mypy --strict. `authority.py` is in `core/` (purity-globbed) — dataclasses/typing only.

---

## File structure
- **Create `src/teamctx/core/authority.py`** — `AuthorityDecl`, `AuthorityState`, `AuthorityEntry`, `assess_authority`.
- **Modify `src/teamctx/core/select.py`** — `ContextSelection.authority`; `select_context(declarations=())`.
- **Create `tests/test_authority.py`** — S2 unit tests.
- **Modify `tests/test_select.py`** — integration (authority carried on the selection).

---

## Task 0: Branch + plan
- [ ] `cd /home/eparenti/agents/repos/teamctx && git checkout -b build/slice-08a-authority-core`
- [ ] `git add docs/superpowers/plans/2026-06-19-slice-08a-authority-core.md && git commit -m "docs: slice-08a plan (authority core)"`

---

## Task 1: Core authority logic (`core/authority.py`)

**Files:** Create `src/teamctx/core/authority.py`, `tests/test_authority.py`.

- [ ] **Step 1: Failing tests.** Create `tests/test_authority.py`:
```python
"""Authority: evidence vs. governance. Surface conflict, never adjudicate (pillar S2)."""

from __future__ import annotations

from teamctx.core.authority import AuthorityDecl, AuthorityEntry, assess_authority


def _decl(value: str, priority: int, fresh: bool, source: str) -> AuthorityDecl:
    return AuthorityDecl(
        subject="rounding-cap", source=source, priority=priority, value=value, fresh=fresh
    )


def test_unique_fresh_maximal_authority_resolves() -> None:
    decls = [_decl("3", priority=10, fresh=True, source="policy")]
    assert assess_authority("rounding-cap", decls) == AuthorityEntry(
        "rounding-cap", "resolved", "3"
    )


def test_two_fresh_maximal_with_divergent_values_is_conflicted_and_picks_nothing() -> None:
    decls = [
        _decl("5", priority=10, fresh=True, source="ticket-mirror"),
        _decl("3", priority=10, fresh=True, source="policy-mirror"),
    ]
    entry = assess_authority("rounding-cap", decls)
    assert entry.state == "conflicted"
    assert entry.value is None  # refuse to pick


def test_stale_high_priority_is_not_overridden_by_fresh_low_priority() -> None:
    # the policy-sensitive case: stale HIGH authority + fresh LOW authority.
    decls = [
        _decl("3", priority=10, fresh=False, source="policy"),  # authoritative but stale
        _decl("5", priority=1, fresh=True, source="ticket"),  # fresh but lower priority
    ]
    entry = assess_authority("rounding-cap", decls)
    assert entry.state == "unknown[stale-authority]"
    assert entry.value is None  # NOT resolved to the fresh low-priority ticket


def test_no_applicable_declaration_is_missing() -> None:
    assert assess_authority("rounding-cap", []) == AuthorityEntry("rounding-cap", "missing", None)


def test_only_declarations_for_the_subject_apply() -> None:
    decls = [AuthorityDecl(subject="other", source="x", priority=10, value="9", fresh=True)]
    assert assess_authority("rounding-cap", decls).state == "missing"
```

- [ ] **Step 2: Run** `pytest tests/test_authority.py -v` — FAIL (module missing).

- [ ] **Step 3: Implement.** Create `src/teamctx/core/authority.py`:
```python
"""Authority: governance declarations, separate from observed evidence.

Authority answers *what should be true* (declared), never *what is observed*. The broker
**surfaces conflict and refuses to adjudicate**, and **never lets a fresh lower-priority
source override a stale higher-priority one** — silently falling through to the fresh lower
source would be exactly the absence-implies-safety failure the model forbids.

Declarations are assumed already projected to the consumer-visible set (Delta_P): the loader
filters by ``can_read`` before passing them here, so authority over invisible sources
contributes nothing (preserving existence-privacy).

Pure: dataclasses + typing only (the core purity test guards it).
"""

from __future__ import annotations

from collections.abc import Iterable
from dataclasses import dataclass
from typing import Literal

AuthorityState = Literal[
    "resolved",
    "missing",
    "conflicted",
    "unknown[stale-authority]",
]


@dataclass(frozen=True)
class AuthorityDecl:
    """A governance declaration: a ``source`` is authoritative for ``subject`` at ``priority``,
    declaring ``value``; ``fresh`` is whether the declaring source is within its window."""

    subject: str
    source: str
    priority: int
    value: str
    fresh: bool


@dataclass(frozen=True)
class AuthorityEntry:
    """The resolved authority state for a subject. ``value`` is set only when ``resolved``."""

    subject: str
    state: AuthorityState
    value: str | None


def assess_authority(subject: str, declarations: Iterable[AuthorityDecl]) -> AuthorityEntry:
    """Resolve the authority state for ``subject`` over the (already P-visible) declarations.

    ``missing`` if none apply; ``unknown[stale-authority]`` if the priority-maximal authority
    is present but stale (never overridden by a fresh lower-priority source); ``conflicted``
    if two or more fresh priority-maximal declarations disagree (refuse to pick); ``resolved``
    only when a unique fresh priority-maximal value stands.
    """

    applies = [decl for decl in declarations if decl.subject == subject]
    if not applies:
        return AuthorityEntry(subject, "missing", None)

    max_priority = max(decl.priority for decl in applies)
    maximal = [decl for decl in applies if decl.priority == max_priority]
    fresh_maximal = [decl for decl in maximal if decl.fresh]
    if not fresh_maximal:
        return AuthorityEntry(subject, "unknown[stale-authority]", None)

    values = {decl.value for decl in fresh_maximal}
    if len(values) > 1:
        return AuthorityEntry(subject, "conflicted", None)
    return AuthorityEntry(subject, "resolved", next(iter(values)))
```

- [ ] **Step 4:** `pytest tests/test_authority.py -v` PASS; `ruff check src tests`; `mypy src` clean; purity guard still passes (new core file).

- [ ] **Step 5: Commit**
```bash
git add src/teamctx/core/authority.py tests/test_authority.py
git commit -m "feat: core authority logic (resolved/missing/conflicted/stale; refuse-to-pick)"
```

---

## Task 2: Carry authority on the broker answer

**Files:** `src/teamctx/core/select.py`, `tests/test_select.py`.

- [ ] **Step 1: Failing test.** In `tests/test_select.py` add `from teamctx.core.authority import AuthorityDecl`. Append:
```python
def test_select_context_carries_authority_for_declared_subjects() -> None:
    document = load_document()
    declarations = [
        AuthorityDecl(subject="rounding-cap", source="policy", priority=10, value="3", fresh=True),
    ]
    selection = select_context(
        document.request_context,
        document.source_signals,
        document.source_statuses,
        declarations,
    )
    assert len(selection.authority) == 1
    assert selection.authority[0].subject == "rounding-cap"
    assert selection.authority[0].state == "resolved"


def test_select_context_with_no_declarations_has_empty_authority() -> None:
    document = load_document()
    selection = select_context(
        document.request_context, document.source_signals, document.source_statuses
    )
    assert selection.authority == ()
```

- [ ] **Step 2: Run** `pytest tests/test_select.py -v` — FAIL (`select_context` takes no declarations / `ContextSelection` has no `authority`).

- [ ] **Step 3: Implement** in `src/teamctx/core/select.py`:
- Import: `from teamctx.core.authority import AuthorityDecl, AuthorityEntry, assess_authority`.
- Add `authority` to `ContextSelection` (after `closure`):
```python
@dataclass(frozen=True)
class ContextSelection:
    """The broker's answer at work-start: rendered cards, the typed certified claims (C), the
    untrusted hint layer (H), honest coverage, per-proposition closure, and per-subject
    authority state."""

    cards: tuple[ContextCard, ...]
    claim_cards: tuple[ClaimCard, ...]
    hints: tuple[Hint, ...]
    coverage: Coverage
    closure: tuple[ClosureEntry, ...]
    authority: tuple[AuthorityEntry, ...]
```
- Update `select_context` to take declarations and compute authority:
```python
def select_context(
    request: RequestContext,
    signals: Iterable[SourceSignal],
    statuses: Iterable[SourceStatus],
    declarations: Iterable[AuthorityDecl] = (),
) -> ContextSelection:
    """Broker entry point: derive typed claims, render cards, report coverage + closure, and
    resolve per-subject authority (surfacing conflict, never adjudicating)."""

    declaration_list = list(declarations)
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
    subjects = sorted({decl.subject for decl in declaration_list})
    authority = tuple(assess_authority(subject, declaration_list) for subject in subjects)
    return ContextSelection(
        cards=cards,
        claim_cards=claim_cards,
        hints=(),
        coverage=coverage,
        closure=closure,
        authority=authority,
    )
```

- [ ] **Step 4: Full gate.** `grep -rn "ContextSelection(" src tests` — only `select_context`; if a test constructs it directly, add `authority=()`. Then `pytest` (existing select/render/cli/evaluate tests pass — `authority` is additive and defaults empty), `ruff check src tests`, `mypy src`.

- [ ] **Step 5: Commit**
```bash
git add src/teamctx/core/select.py tests/test_select.py
git commit -m "feat: carry per-subject authority on the broker answer (kappa.authority)"
```

---

## Task 3: Verify
- [ ] `pytest && ruff check src tests && mypy src` green; purity guard passes (covers `authority.py`).

**Definition of done:** `assess_authority` resolves/conflicts/misses, refuses to pick on conflict, and never overrides a stale high-priority authority with a fresh low-priority one; `ContextSelection.authority` carries it; gate green. (S2 surfaced in the engine.)

## Notes for slice 8b
8b adds: a `.teamctx/authority.json` loader (I/O, OUTSIDE core — e.g. `connectors/declared_authority.py`) that filters to `can_read` sources (Delta_P) and returns `AuthorityDecl`s; CLI wiring to load + pass declarations; and render lines for authority (resolved value / "CONFLICTED — sources disagree, not adjudicated" / "stale authority — refresh"). Deferred from the thin slice: temporary-override states, graduated `.teamctx`→durable, dissent cards, precision tuning.
