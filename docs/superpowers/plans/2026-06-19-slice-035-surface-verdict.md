# Slice 3.5: Surface the Verdict in `work-start` Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development or superpowers:executing-plans. Steps use checkbox (`- [ ]`) syntax.

**Goal:** Make the engine's honest answer legible to a user: `work-start` shows a one-line conflict verdict ("NOT CLEAR / clear / UNKNOWN, absence is not an all-clear"), computed by the `evaluate` SDK from slice 3. This is the last step before the dogfood checkpoint.

**Architecture:** The consumer (the CLI) computes the verdict via `evaluate(no_conflict_query(request), selection.claim_cards, selection.closure)` and passes it to `render_selection`, which appends a verdict line. `evaluate` stays out of `select.py`; the render layer (`contract_render.py`, not in `core/`) may import it. Import graph stays acyclic: `cli → {select, evaluate, contract_render}`, `contract_render → {select, evaluate}`, `evaluate → {select, prop}`.

**Tech Stack:** Python 3.12, click, pytest, ruff, mypy --strict.

---

## File structure
- **Modify `src/teamctx/contract_render.py`**: `render_selection` gains an optional `verdict` param; add `_verdict_line` helper.
- **Modify `src/teamctx/cli.py`**: `work-start` computes the verdict and passes it to `render_selection`.
- **Modify `tests/test_render_selection.py`**: verdict-line rendering tests.
- **Modify `tests/test_work_start_cli.py`**: assert the verdict line in the no-token path.

---

## Task 0: Branch and commit the plan
- [ ] `git checkout -b build/slice-035-surface-verdict`
- [ ] `git add docs/superpowers/plans/2026-06-19-slice-035-surface-verdict.md && git commit -m "docs: slice-3.5 plan (surface verdict in work-start)"`

---

## Task 1: Render the verdict line + wire the CLI

**Files:** Modify `src/teamctx/contract_render.py`, `src/teamctx/cli.py`, `tests/test_render_selection.py`, `tests/test_work_start_cli.py`.

- [ ] **Step 1: Write the failing tests.**

In `tests/test_render_selection.py`, add import `from teamctx.core.evaluate import Valuation` and append:
```python
def test_render_appends_not_clear_verdict_for_a_false_valuation() -> None:
    document = load_document()
    selection = select_context(
        document.request_context, document.source_signals, document.source_statuses
    )
    text = render_selection(selection, Valuation("false"))
    assert "Conflict check: NOT CLEAR" in text


def test_render_appends_clear_verdict_for_a_true_valuation() -> None:
    document = load_document()
    selection = select_context(
        document.request_context, document.source_signals, document.source_statuses
    )
    text = render_selection(selection, Valuation("true"))
    assert "Conflict check: clear" in text


def test_render_appends_unknown_verdict_with_reason() -> None:
    document = load_document()
    selection = select_context(
        document.request_context, document.source_signals, document.source_statuses
    )
    text = render_selection(selection, Valuation("unknown", "incomplete[stale-dep]"))
    assert "Conflict check: UNKNOWN" in text
    assert "incomplete[stale-dep]" in text
    assert "absence is not an all-clear" in text


def test_render_without_a_verdict_is_unchanged() -> None:
    document = load_document()
    selection = select_context(
        document.request_context, document.source_signals, document.source_statuses
    )
    assert "Conflict check" not in render_selection(selection)
```

In `tests/test_work_start_cli.py`, add to the existing `test_work_start_with_no_token_degrades_honestly` (after the current asserts):
```python
    # the engine's verdict is surfaced: no token => unknown, never a false "clear".
    assert "Conflict check: UNKNOWN" in result.output
```

- [ ] **Step 2: Run** `pytest tests/test_render_selection.py tests/test_work_start_cli.py -v`, expect FAIL (`render_selection` takes no `verdict`; no "Conflict check" line).

- [ ] **Step 3: Implement.**

In `src/teamctx/contract_render.py`: add an import `from teamctx.core.evaluate import Valuation`. Change `render_selection`'s signature to:
```python
def render_selection(selection: ContextSelection, verdict: Valuation | None = None) -> str:
```
At the END of `render_selection`, just before `return "\n".join(lines) + "\n"`, insert:
```python
    if verdict is not None:
        lines.extend(["", _verdict_line(verdict)])
```
Add the helper (top-level function in the same module):
```python
def _verdict_line(verdict: Valuation) -> str:
    """One-line human verdict for the work-start conflict query."""

    if verdict.value == "false":
        return "Conflict check: NOT CLEAR, an open PR conflicts with your changes (see above)."
    if verdict.value == "true":
        return "Conflict check: clear, no conflicting open PRs, coverage complete."
    return (
        f"Conflict check: UNKNOWN, coverage incomplete ({verdict.reason}); "
        "absence is not an all-clear."
    )
```

In `src/teamctx/cli.py`: add imports `from teamctx.core.evaluate import evaluate` and `no_conflict_query` to the existing `from teamctx.core.select import ...` line (currently imports `select_context`). In `work_start_command`, replace:
```python
    selection = select_context(
        document.request_context, document.source_signals, document.source_statuses
    )
    click.echo(render_selection(selection), nl=False)
```
with:
```python
    selection = select_context(
        document.request_context, document.source_signals, document.source_statuses
    )
    verdict = evaluate(
        no_conflict_query(document.request_context),
        selection.claim_cards,
        selection.closure,
    )
    click.echo(render_selection(selection, verdict), nl=False)
```

- [ ] **Step 4: Run the full gate.**
- `pytest`, all pass (the four new render tests; the updated CLI test; everything else green, existing `render_selection(selection)` calls still work via the optional default).
- `ruff check src tests`, clean.
- `mypy src`, Success.

- [ ] **Step 5: Commit**
```bash
git add src/teamctx/contract_render.py src/teamctx/cli.py tests/test_render_selection.py tests/test_work_start_cli.py
git commit -m "feat: surface the conflict verdict in work-start output"
```

---

## Task 2: Verify
- [ ] `pytest && ruff check src tests && mypy src`, green.
- [ ] Acyclic check: `grep -n "evaluate" src/teamctx/core/select.py` returns nothing.
- [ ] Live smoke: `GITHUB_TOKEN=$(gh auth token) PYTHONPATH=src python -m teamctx.cli work-start --github-repo ostinato-forge/project-foundry --path docs/foundry-v2-build-plan.md`, now ends with a `Conflict check:` line (expected NOT CLEAR, since PR #14 is a real collision on that path).

**Definition of done:** `work-start` ends with an honest one-line verdict driven by `evaluate`; no-token path shows UNKNOWN (never a false "clear"); existing output otherwise unchanged; gate green; imports acyclic.

---

## Notes for the next step (do not implement here)
This completes the minimal honest engine with a legible verdict, the **dogfood checkpoint**. Next is the two-agent live test (Mike+agent / Ed+agent, shared repo, cross-user PR collisions), then breadth (slices 5–9). The verdict wording (`_verdict_line`) is intentionally plain; expect to tune it from dogfood feedback.
