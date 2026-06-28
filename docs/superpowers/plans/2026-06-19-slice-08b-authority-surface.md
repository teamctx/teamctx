# Slice 8b: Thin Authority: `.teamctx` Loader + CLI + Render

> REQUIRED SUB-SKILL: superpowers:subagent-driven-development. Checkbox steps.

**Goal:** Make authority usable end to end. Load governance declarations from a `.teamctx/authority.json` file (I/O, outside core), pass them to the broker, and render an **Authority** section in `work-start` (resolved value / **CONFLICTED, not adjudicated** / stale-authority).

**Architecture:** `connectors/declared_authority.py` reads the file → `AuthorityDecl`s (the file is the consumer's Δ_P declaration set, you only read declarations you have access to). The CLI loads `.teamctx/authority.json` from cwd and passes them to `select_context`. `render_selection` renders `selection.authority` (already on the answer from 8a) as an Authority section.

**Tech Stack:** Python 3.12, click, pathlib/json (in the connector, NOT core), pytest, ruff, mypy --strict.

---

## File structure
- **Create `src/teamctx/connectors/declared_authority.py`**: `load_declared_authority(path) -> list[AuthorityDecl]` (I/O).
- **Modify `src/teamctx/contract_render.py`**: render an Authority section from `selection.authority`.
- **Modify `src/teamctx/cli.py`**: `work-start` loads `.teamctx/authority.json` + passes declarations.
- **Create `tests/test_declared_authority.py`**: loader tests.
- **Modify `tests/test_render_selection.py`**: Authority section render test.

---

## Task 0: Branch + plan
- [ ] `cd /home/eparenti/agents/repos/teamctx && git checkout -b build/slice-08b-authority-surface`
- [ ] `git add docs/superpowers/plans/2026-06-19-slice-08b-authority-surface.md && git commit -m "docs: slice-08b plan (authority loader + surface)"`

---

## Task 1: The `.teamctx/authority.json` loader

**Files:** Create `src/teamctx/connectors/declared_authority.py`, `tests/test_declared_authority.py`.

- [ ] **Step 1: Failing tests.** Create `tests/test_declared_authority.py`:
```python
"""Loading declared authority from a .teamctx file (the consumer's Delta_P declaration set)."""

from __future__ import annotations

import json
from pathlib import Path

from teamctx.connectors.declared_authority import load_declared_authority
from teamctx.core.authority import AuthorityDecl


def test_absent_file_yields_no_declarations(tmp_path: Path) -> None:
    assert load_declared_authority(tmp_path / "nope.json") == []


def test_loads_declarations_from_json(tmp_path: Path) -> None:
    path = tmp_path / "authority.json"
    path.write_text(
        json.dumps(
            [
                {
                    "subject": "rounding-cap",
                    "source": "confluence:Rounding Policy",
                    "priority": 10,
                    "value": "3",
                    "fresh": True,
                }
            ]
        ),
        encoding="utf-8",
    )
    decls = load_declared_authority(path)
    assert decls == [
        AuthorityDecl(
            subject="rounding-cap",
            source="confluence:Rounding Policy",
            priority=10,
            value="3",
            fresh=True,
        )
    ]
```

- [ ] **Step 2: Run** `pytest tests/test_declared_authority.py -v`, FAIL (module missing).

- [ ] **Step 3: Implement.** Create `src/teamctx/connectors/declared_authority.py`:
```python
"""Load declared authority from a .teamctx file.

This is the I/O edge for governance declarations, it lives OUTSIDE the pure core. The file
is treated as the consumer's visible declaration set (Delta_P): a consumer only reads
declarations it has access to, so authority over invisible sources never enters here. Real
source freshness is observed upstream; the thin loader takes a declared ``fresh`` flag.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any, cast

from teamctx.core.authority import AuthorityDecl


def load_declared_authority(path: Path) -> list[AuthorityDecl]:
    """Read declared authority from ``path``. Returns ``[]`` if the file does not exist."""

    if not path.exists():
        return []
    data = cast("list[dict[str, Any]]", json.loads(path.read_text(encoding="utf-8")))
    return [
        AuthorityDecl(
            subject=str(item["subject"]),
            source=str(item["source"]),
            priority=int(item["priority"]),
            value=str(item["value"]),
            fresh=bool(item["fresh"]),
        )
        for item in data
    ]
```

- [ ] **Step 4:** `pytest tests/test_declared_authority.py -v` PASS; `ruff check src tests`; `mypy src` clean. (Purity guard unaffected, this is a connector, not `core/`.)

- [ ] **Step 5: Commit**
```bash
git add src/teamctx/connectors/declared_authority.py tests/test_declared_authority.py
git commit -m "feat: .teamctx declared-authority loader (I/O edge, outside core)"
```

---

## Task 2: Render the Authority section + wire the CLI

**Files:** `src/teamctx/contract_render.py`, `src/teamctx/cli.py`, `tests/test_render_selection.py`.

- [ ] **Step 1: Failing test.** In `tests/test_render_selection.py` add `from teamctx.core.authority import AuthorityDecl`. Append:
```python
def test_render_shows_an_authority_section_with_conflict_surfaced() -> None:
    document = load_document()
    declarations = [
        AuthorityDecl(subject="rounding-cap", source="ticket", priority=10, value="5", fresh=True),
        AuthorityDecl(subject="rounding-cap", source="policy", priority=10, value="3", fresh=True),
    ]
    selection = select_context(
        document.request_context,
        document.source_signals,
        document.source_statuses,
        declarations,
    )
    text = render_selection(selection)
    assert "Authority" in text
    assert "rounding-cap" in text
    assert "CONFLICTED" in text  # surfaced, not adjudicated


def test_render_has_no_authority_section_without_declarations() -> None:
    document = load_document()
    selection = select_context(
        document.request_context, document.source_signals, document.source_statuses
    )
    assert "Authority" not in render_selection(selection)
```

- [ ] **Step 2: Run** `pytest tests/test_render_selection.py -v`, FAIL (no Authority section).

- [ ] **Step 3: Implement.**

In `src/teamctx/contract_render.py`: add `from teamctx.core.authority import AuthorityEntry`. Add a helper:
```python
def _authority_line(entry: AuthorityEntry) -> str:
    if entry.state == "resolved":
        return f"- {entry.subject}: resolved (value {entry.value})"
    if entry.state == "conflicted":
        return f"- {entry.subject}: CONFLICTED, declared sources disagree; not adjudicated"
    if entry.state == "unknown[stale-authority]":
        return f"- {entry.subject}: unknown, declared authority is stale; refresh it"
    return f"- {entry.subject}: no authority declared"
```
In `render_selection`, after the Coverage block and BEFORE the verdict loop (or after, pick a consistent order; put Authority after Coverage, before verdicts), insert:
```python
    if selection.authority:
        lines.extend(["", "Authority"])
        lines.extend(_authority_line(entry) for entry in selection.authority)
```

In `src/teamctx/cli.py`: add `from teamctx.connectors.declared_authority import load_declared_authority`. In `work_start_command`, load declarations and pass them to `select_context`:
```python
    declarations = load_declared_authority(Path(".teamctx/authority.json"))
    selection = select_context(
        document.request_context,
        document.source_signals,
        document.source_statuses,
        declarations,
    )
```
(`Path` is already imported in cli.py.)

- [ ] **Step 4: Full gate.** `pytest` (existing render tests without declarations still pass, Authority section only appears when `selection.authority` is non-empty; CLI tests: the no-token test doesn't create a `.teamctx/authority.json`, so declarations=[] and no Authority section, unchanged). `ruff check src tests`; `mypy src`.

- [ ] **Step 5: Commit**
```bash
git add src/teamctx/contract_render.py src/teamctx/cli.py tests/test_render_selection.py
git commit -m "feat: surface an Authority section in work-start (load .teamctx, render conflict honestly)"
```

---

## Task 3: Verify
- [ ] `pytest && ruff check src tests && mypy src` green; purity guard passes.
- [ ] Optional manual: create `.teamctx/authority.json` with two divergent fresh priority-10 decls for a subject, run `work-start`, the Authority section shows `CONFLICTED, declared sources disagree; not adjudicated`.

**Definition of done:** `work-start` loads `.teamctx/authority.json` and renders an Authority section that surfaces conflict without adjudicating and flags stale authority; absent file → no section, no behavior change; gate green. Thin authority (slice 8) is complete end to end.

## Notes for slice 9
Slice 9: replay/snapshot (T1 verifiable replay), structured `why{reason_code,params}` (#11), severity decomposition + conformance fixture (#6). The dogfood's "card says THAT not WHAT" legibility can fold into the structured-why work.
