# Slice 9a: Verifiable Replay (T1): Snapshot Digest

> REQUIRED SUB-SKILL: superpowers:subagent-driven-development. Checkbox steps.

**Goal:** Make determinism verifiable (Theorem 1). The broker answer carries a **content-addressed snapshot digest** binding the exact inputs (request, signals, statuses, declarations), so a verifier can confirm a replay: same inputs → same digest → same ⟨C, κ⟩.

**Architecture:** `core/snapshot.py` (pure, `json` + `hashlib`, both deterministic and not I/O) computes a `snapshot_digest` over the canonical serialization of the inputs. `select_context` materializes its inputs once, computes the digest, and carries it on `ContextSelection`.

**Tech Stack:** Python 3.12, `hashlib`/`json` (deterministic, allowed in core, the purity test bans only os/pathlib/time/datetime/random/secrets/subprocess/tempfile), pydantic models, frozen dataclasses, pytest, ruff, mypy --strict.

---

## File structure
- **Create `src/teamctx/core/snapshot.py`**: `snapshot_digest(request, signals, statuses, declarations) -> str`.
- **Modify `src/teamctx/core/select.py`**: materialize inputs once; `ContextSelection.snapshot_digest: str`; compute it in `select_context`.
- **Create `tests/test_snapshot.py`**: digest determinism + sensitivity.
- **Modify `tests/test_select.py`**: replay (two identical calls → equal selections, same digest).

---

## Task 0: Branch + plan
- [ ] `cd /home/eparenti/agents/repos/teamctx && git checkout -b build/slice-09a-replay-snapshot`
- [ ] `git add docs/superpowers/plans/2026-06-19-slice-09a-replay-snapshot.md && git commit -m "docs: slice-09a plan (verifiable replay / snapshot digest)"`

---

## Task 1: `snapshot_digest`

**Files:** Create `src/teamctx/core/snapshot.py`, `tests/test_snapshot.py`.

- [ ] **Step 1: Failing tests.** Create `tests/test_snapshot.py`:
```python
"""Verifiable replay (Theorem 1): the snapshot digest binds the exact inputs."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any, cast

from teamctx.core.contracts import CoreContractDocument
from teamctx.core.snapshot import snapshot_digest

ROOT = Path(__file__).resolve().parent.parent
FIXTURE = ROOT / "docs/product/discovery/fixtures/contracts/v0/core-contract-document.json"


def _document() -> CoreContractDocument:
    data = cast("dict[str, Any]", json.loads(FIXTURE.read_text(encoding="utf-8")))
    return CoreContractDocument.model_validate(data)


def test_digest_is_stable_for_identical_inputs() -> None:
    doc = _document()
    a = snapshot_digest(doc.request_context, doc.source_signals, doc.source_statuses, [])
    b = snapshot_digest(doc.request_context, doc.source_signals, doc.source_statuses, [])
    assert a == b
    assert len(a) == 64  # sha256 hex


def test_digest_changes_when_an_input_changes() -> None:
    doc = _document()
    base = snapshot_digest(doc.request_context, doc.source_signals, doc.source_statuses, [])
    other_request = doc.request_context.model_copy(update={"paths": ["src/changed.py"]})
    changed = snapshot_digest(other_request, doc.source_signals, doc.source_statuses, [])
    assert base != changed


def test_digest_is_order_independent_for_signals() -> None:
    doc = _document()
    a = snapshot_digest(doc.request_context, doc.source_signals, doc.source_statuses, [])
    b = snapshot_digest(
        doc.request_context, list(reversed(doc.source_signals)), doc.source_statuses, []
    )
    assert a == b
```

- [ ] **Step 2: Run** `pytest tests/test_snapshot.py -v`, FAIL (module missing).

- [ ] **Step 3: Implement.** Create `src/teamctx/core/snapshot.py`:
```python
"""Verifiable replay (Theorem 1): a content-addressed digest binding the broker's inputs.

The digest is a deterministic function of the canonical serialization of the request, the
observed signals and statuses, and the governance declarations. Same inputs → same digest →
same answer; a verifier re-derives and confirms the binding. Pure: ``json`` + ``hashlib``
are deterministic and do no I/O (the core purity test bans only os/pathlib/time/etc.).
"""

from __future__ import annotations

import hashlib
import json
from collections.abc import Iterable
from dataclasses import asdict
from typing import Any

from teamctx.core.authority import AuthorityDecl
from teamctx.core.contracts import RequestContext, SourceSignal, SourceStatus


def snapshot_digest(
    request: RequestContext,
    signals: Iterable[SourceSignal],
    statuses: Iterable[SourceStatus],
    declarations: Iterable[AuthorityDecl],
) -> str:
    """A sha256 hex digest binding the exact inputs that produced an answer (order-independent
    for the source/declaration sets)."""

    payload: dict[str, Any] = {
        "request": request.model_dump(mode="json"),
        "signals": sorted(
            (signal.model_dump(mode="json") for signal in signals), key=lambda item: item["id"]
        ),
        "statuses": sorted(
            (status.model_dump(mode="json") for status in statuses),
            key=lambda item: item["source_id"],
        ),
        "declarations": sorted(
            (asdict(decl) for decl in declarations),
            key=lambda item: (item["subject"], item["source"]),
        ),
    }
    canonical = json.dumps(payload, sort_keys=True, separators=(",", ":"))
    return hashlib.sha256(canonical.encode("utf-8")).hexdigest()
```

- [ ] **Step 4:** `pytest tests/test_snapshot.py -v` PASS; `ruff check src tests`; `mypy src` clean; **purity guard still passes** (run `pytest tests/test_core_contracts.py::test_core_package_has_no_file_or_runtime_side_effect_imports -q`, `json`/`hashlib` are not banned).

- [ ] **Step 5: Commit**
```bash
git add src/teamctx/core/snapshot.py tests/test_snapshot.py
git commit -m "feat: snapshot digest binding broker inputs (verifiable replay, T1)"
```

---

## Task 2: Carry the digest on the answer

**Files:** `src/teamctx/core/select.py`, `tests/test_select.py`.

- [ ] **Step 1: Failing test.** Append to `tests/test_select.py`:
```python
def test_select_context_is_replayable_with_a_stable_digest() -> None:
    document = load_document()
    a = select_context(
        document.request_context, document.source_signals, document.source_statuses
    )
    b = select_context(
        document.request_context, document.source_signals, document.source_statuses
    )
    # determinism: identical inputs -> identical answer, bound by an identical digest.
    assert a == b
    assert a.snapshot_digest == b.snapshot_digest
    assert len(a.snapshot_digest) == 64
```

- [ ] **Step 2: Run** `pytest tests/test_select.py -v`, FAIL (`ContextSelection` has no `snapshot_digest`).

- [ ] **Step 3: Implement** in `src/teamctx/core/select.py`:
- Import: `from teamctx.core.snapshot import snapshot_digest`.
- Add `snapshot_digest: str` as the last field of `ContextSelection`.
- In `select_context`, materialize signals + statuses once (so they can be both consumed and digested), and compute the digest:
```python
def select_context(
    request: RequestContext,
    signals: Iterable[SourceSignal],
    statuses: Iterable[SourceStatus],
    declarations: Iterable[AuthorityDecl] = (),
) -> ContextSelection:
    """Broker entry point: derive typed claims, render cards, report coverage + closure,
    resolve authority, and bind the inputs with a verifiable-replay digest."""

    signal_list = list(signals)
    status_list = list(statuses)
    declaration_list = list(declarations)
    coverage = build_coverage(status_list)
    claim_cards = tuple(derive_claims(request, signal_list))
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
    digest = snapshot_digest(request, signal_list, status_list, declaration_list)
    return ContextSelection(
        cards=cards,
        claim_cards=claim_cards,
        hints=(),
        coverage=coverage,
        closure=closure,
        authority=authority,
        snapshot_digest=digest,
    )
```
(Keep the `ContextSelection` dataclass fields in this order: cards, claim_cards, hints, coverage, closure, authority, snapshot_digest.)

- [ ] **Step 4: Full gate.** `grep -rn "ContextSelection(" src tests` (only `select_context`; add `snapshot_digest=...` only there). `pytest`, all pass (existing tests read other fields; `snapshot_digest` is additive; equality tests like the replay test now also cover the digest). `ruff check src tests`; `mypy src`.

- [ ] **Step 5: Commit**
```bash
git add src/teamctx/core/select.py tests/test_select.py
git commit -m "feat: carry the verifiable-replay digest on the broker answer"
```

---

## Task 3: Verify
- [ ] `pytest && ruff check src tests && mypy src` green; purity guard passes (covers `snapshot.py`).

**Definition of done:** `snapshot_digest` deterministically binds the inputs (stable, order-independent for sets, sensitive to changes); `ContextSelection.snapshot_digest` carries it; `select_context` is provably replayable (identical inputs → equal answer + equal digest); gate green. (T1 in code.)

## Notes for slice 9b
9b: structured `why{reason_code, params}` (#11) on cards (each kind's render sets a machine-readable `reason_code`; the prose `reason` is derived) + severity decomposition (#6) (`severity = clamp01(kind_base × (1+α·magnitude) × scope_mult)`, decomposition retained on the card) + a severity conformance fixture. The dogfood's "card says THAT not WHAT" legibility can fold in (a reason_code/param that names the source to open).
