# Slice 6 — `criteria-changed` Card Kind + Multi-Verdict Rendering

> REQUIRED SUB-SKILL: superpowers:subagent-driven-development. Checkbox steps.

**Goal:** Add the second card kind — **criteria-changed** (a linked issue's acceptance criteria changed) — by registration on the slice-5 engine, and light up the multi-kind path: `work-start` now shows one verdict line **per registered kind**. Fixture/in-test signals prove it (the live issue-tracker connector is a separate layer).

**Architecture:** Register `criteria_changed` as a `CardKind` (predicate `issue_criteria_changed` refutes universal `no_criteria_changed_for_issues`, over the request's `linked_issues`, deps = `issue_tracker`). Give `CardKind` a `verdict_label`. The CLI computes a verdict per kind via `evaluate(kind.query(request), ...)` and `render_selection` renders one labeled line per verdict.

**Tech Stack:** Python 3.12, pydantic contracts, frozen dataclasses, pytest, ruff, mypy --strict.

---

## File structure
- `src/teamctx/core/contracts.py` — add `"criteria_changed"` to `SignalType`.
- `src/teamctx/core/prop.py` — register predicates + refutes-pair.
- `src/teamctx/core/select.py` — `criteria_changed_query`, `_derive_criteria_changed_claim`, `render_criteria_changed_claim`, deps entry, `CardKind.verdict_label`, `CARD_KINDS` entry.
- `src/teamctx/contract_render.py` — `render_selection` renders a labeled verdict line per verdict (multi).
- `src/teamctx/cli.py` — compute a verdict per kind, pass to render.
- Tests: `tests/test_select.py`, `tests/test_render_selection.py`, `tests/test_work_start_cli.py`.

---

## Task 0: Branch + plan
- [ ] `cd /home/eparenti/agents/repos/teamctx && git checkout -b build/slice-06-criteria-changed`
- [ ] `git add docs/superpowers/plans/2026-06-19-slice-06-criteria-changed.md && git commit -m "docs: slice-06 plan (criteria-changed + multi-verdict)"`

---

## Task 1: Register the criteria-changed kind

**Files:** `contracts.py`, `prop.py`, `select.py`, `tests/test_select.py`.

- [ ] **Step 1: Failing tests.** In `tests/test_select.py`, add to imports: `from teamctx.core.contracts import PolicyDecision, SourceSignal` (SourceSignal may already be imported — merge). Add to the `teamctx.core.select` import group: `criteria_changed_query`. Add helper + tests:
```python
def _criteria_signal(issue: str, repo: str = "auth-service") -> SourceSignal:
    return SourceSignal(
        schema_version="teamctx.source_signal.v0",
        id=f"sig_criteria_{issue}",
        signal_type="criteria_changed",
        source_family="issue_tracker",
        scope={"repo": repo, "issue": issue},
        evidence_summary=f"Acceptance criteria for {issue} changed.",
        source_display=f"Issue {issue}",
        freshness="fresh",
        confidence="high",
        visibility="visible",
        created_at="2026-01-01T00:00:00Z",
        observed_at="2026-01-01T00:00:00Z",
        expires_at="next_refresh",
        policy=PolicyDecision(
            schema_version="teamctx.policy_decision.v0",
            can_render_to_user=True,
            can_render_to_agent=True,
            can_include_source_text=False,
            requires_review_for_guidance=False,
            decision_reason="issue metadata is allowed as evidence",
        ),
    )


def test_criteria_changed_derives_a_claim_for_a_linked_issue() -> None:
    document = load_document()
    request = document.request_context.model_copy(update={"linked_issues": ["PROJ-123"]})

    claim_cards = derive_claims(request, [_criteria_signal("PROJ-123")])

    assert len(claim_cards) == 1
    assert claim_cards[0].claim.predicate == "issue_criteria_changed"
    assert witnesses(claim_cards[0].claim, criteria_changed_query(request)) == "refutes"


def test_criteria_changed_ignores_an_unlinked_issue() -> None:
    document = load_document()
    request = document.request_context.model_copy(update={"linked_issues": ["PROJ-999"]})

    assert derive_claims(request, [_criteria_signal("PROJ-123")]) == []


def test_select_context_now_has_two_closure_entries() -> None:
    document = load_document()
    selection = select_context(
        document.request_context, document.source_signals, document.source_statuses
    )
    props = {e.proposition for e in selection.closure}
    assert props == {"no_pr_conflicts_with_paths", "no_criteria_changed_for_issues"}
```

- [ ] **Step 2: Run** `pytest tests/test_select.py -v` — FAIL (`criteria_changed` not a valid SignalType / `criteria_changed_query` missing).

- [ ] **Step 3: Implement.**

`src/teamctx/core/contracts.py`: add `"criteria_changed"` to the `SignalType` Literal (e.g. after `"collision"`).

`src/teamctx/core/prop.py`: in `PREDICATE_REGISTRY` add `"issue_criteria_changed": "existential"` and `"no_criteria_changed_for_issues": "universal"`. In `REFUTES_PAIRS` add `("issue_criteria_changed", "no_criteria_changed_for_issues")`.

`src/teamctx/core/select.py`:
- Add the query constructor (near `no_conflict_query`):
```python
def criteria_changed_query(request: RequestContext) -> Prop:
    """The universal a criteria-changed card refutes: 'no acceptance criteria changed for
    my linked issues'."""

    return Prop(
        predicate="no_criteria_changed_for_issues",
        subject=SubjectRef(repo=request.repo, paths=tuple(request.linked_issues)),
    )
```
- Add the derive function (near `_derive_collision_claim`):
```python
def _derive_criteria_changed_claim(
    request: RequestContext, signal: SourceSignal
) -> ClaimCard | None:
    issue = signal.scope.get("issue")
    if not isinstance(issue, str) or issue not in request.linked_issues:
        return None
    claim = Prop(
        predicate="issue_criteria_changed",
        subject=SubjectRef(repo=request.repo, paths=(issue,)),
        args=(signal.id,),
    )
    return ClaimCard(claim=claim, signal=signal)
```
- Add the renderer (near `render_collision_claim`):
```python
def render_criteria_changed_claim(claim_card: ClaimCard) -> ContextCard:
    """Render a criteria-changed claim into a human-plane ``ContextCard``."""

    claim = claim_card.claim
    signal = claim_card.signal
    issue = claim.subject.paths[0]
    return ContextCard(
        schema_version="teamctx.context_card.v0",
        id=f"card_{signal.id}",
        section="Verify before relying",
        text=signal.evidence_summary,
        why_this_matters=f"acceptance criteria for {issue} changed; re-check before relying.",
        source_display=signal.source_display,
        refs=[signal.id],
        reason=f"linked issue {issue} had its acceptance criteria changed",
        scope=dict(signal.scope),
        freshness=signal.freshness,
        confidence=signal.confidence,
        source_body="status_only",
        source_open_target_id=None,
        agent_instruction="verify_before_relying",
    )
```
- In `DEPS_REGISTRY` add `"no_criteria_changed_for_issues": frozenset({"issue_tracker"})`.
- Add `verdict_label: str` to `CardKind` (after `signal_type`/`card_predicate`, before the callables, or at the end — pick one and keep all entries consistent).
- Update the collision `CARD_KINDS` entry to include `verdict_label="Conflict check"`, and add the criteria entry:
```python
    CardKind(
        signal_type="criteria_changed",
        card_predicate="issue_criteria_changed",
        verdict_label="Criteria check",
        derive=_derive_criteria_changed_claim,
        query=criteria_changed_query,
        render=render_criteria_changed_claim,
    ),
```
(Place these functions before `CARD_KINDS`. `_RENDER_BY_PREDICATE`/`_KIND_BY_SIGNAL_TYPE` rebuild from `CARD_KINDS` automatically.)

- [ ] **Step 4:** `pytest tests/test_select.py -v` PASS; `ruff check src tests`; `mypy src` clean. The "Verify before relying" section is a valid `SectionName` (it is). Existing collision tests unchanged (collision logic untouched).

- [ ] **Step 5: Commit**
```bash
git add src/teamctx/core/contracts.py src/teamctx/core/prop.py src/teamctx/core/select.py tests/test_select.py
git commit -m "feat: criteria-changed card kind (registered on the multi-kind engine)"
```

---

## Task 2: Multi-verdict rendering (CLI + render)

**Files:** `contract_render.py`, `cli.py`, `tests/test_render_selection.py`, `tests/test_work_start_cli.py`.

- [ ] **Step 1: Failing tests.** Update `tests/test_render_selection.py`: the existing verdict tests pass a single `Valuation`; change `render_selection` calls to pass a tuple of `(label, Valuation)`. Replace those tests' calls, e.g.:
```python
def test_render_appends_labeled_verdicts() -> None:
    document = load_document()
    selection = select_context(
        document.request_context, document.source_signals, document.source_statuses
    )
    text = render_selection(
        selection,
        (("Conflict check", Valuation("false")), ("Criteria check", Valuation("true"))),
    )
    assert "Conflict check: NOT CLEAR" in text
    assert "Criteria check: clear" in text


def test_render_without_verdicts_is_unchanged() -> None:
    document = load_document()
    selection = select_context(
        document.request_context, document.source_signals, document.source_statuses
    )
    assert "check:" not in render_selection(selection)
```
(Delete the prior single-`Valuation` verdict tests that no longer match the signature: `test_render_appends_not_clear_verdict_for_a_false_valuation`, `..._clear_..._true_...`, `..._unknown_..._with_reason`, `test_render_without_a_verdict_is_unchanged`. Keep `test_render_shows_complete_coverage_when_mandated_source_is_fresh` and `test_render_shows_collision_card_and_honest_incomplete_coverage` — they don't pass verdicts.)

`tests/test_work_start_cli.py` — the no-token assertion `"Conflict check: UNKNOWN"` stays valid (collision verdict). It's now joined by a "Criteria check: UNKNOWN" line; the existing substring assert still passes.

- [ ] **Step 2: Run** `pytest tests/test_render_selection.py tests/test_work_start_cli.py -v` — FAIL (`render_selection` signature).

- [ ] **Step 3: Implement.**

In `src/teamctx/contract_render.py`: change the verdict handling to a sequence of labeled verdicts. Replace the `verdict: Valuation | None = None` parameter with:
```python
from collections.abc import Sequence
...
def render_selection(
    selection: ContextSelection,
    verdicts: Sequence[tuple[str, Valuation]] = (),
) -> str:
```
Replace the single-verdict block at the end with:
```python
    for label, verdict in verdicts:
        lines.extend(["", _verdict_line(label, verdict)])
```
And change `_verdict_line` to take the label:
```python
def _verdict_line(label: str, verdict: Valuation) -> str:
    """One labeled human verdict line."""

    if verdict.value == "false":
        return f"{label}: NOT CLEAR — a conflicting open item exists (see above)."
    if verdict.value == "true":
        return f"{label}: clear — coverage complete, nothing conflicting."
    return f"{label}: UNKNOWN — coverage incomplete ({verdict.reason}); absence is not an all-clear."
```

In `src/teamctx/cli.py`: import `CARD_KINDS` from `teamctx.core.select` (add to the existing import). In `work_start_command`, replace the single-verdict computation with:
```python
    verdicts = tuple(
        (
            kind.verdict_label,
            evaluate(kind.query(request_or_doc), selection.claim_cards, selection.closure),
        )
        for kind in CARD_KINDS
    )
    click.echo(render_selection(selection, verdicts), nl=False)
```
NOTE: use the SAME request object `select_context` was called with. In `work_start_command` that is `document.request_context`. So pass `kind.query(document.request_context)`. Remove the now-unused single `no_conflict_query`/`evaluate` single call (keep the imports of `evaluate`; `no_conflict_query` may become unused in cli.py — if so, remove it from the cli import to keep ruff clean).

- [ ] **Step 4: Full gate.**
- `pytest` — all pass. The live/integration tests: `test_open_pr_touching_requested_path...` reads selection fields, unaffected. `test_render_shows_*` unaffected (no verdicts passed).
- `ruff check src tests` — clean (watch for now-unused `no_conflict_query` import in cli.py).
- `mypy src` — Success.

- [ ] **Step 5: Commit**
```bash
git add src/teamctx/contract_render.py src/teamctx/cli.py tests/test_render_selection.py tests/test_work_start_cli.py
git commit -m "feat: multi-verdict work-start output (one labeled verdict per card kind)"
```

---

## Task 3: Verify
- [ ] `pytest && ruff check src tests && mypy src` green.
- [ ] Purity guard passes.
- [ ] Live smoke: `GITHUB_TOKEN=$(gh auth token) PYTHONPATH=src python -m teamctx.cli work-start --github-repo ostinato-forge/project-foundry --path docs/foundry-v2-build-plan.md` — now shows TWO verdict lines: `Conflict check: NOT CLEAR` (PR #14) and `Criteria check: UNKNOWN — coverage incomplete (incomplete[policy-gap])` (no issue-tracker source observed). The collision card + coverage are unchanged.

**Definition of done:** criteria-changed is a registered kind deriving from a linked-issue signal; `work-start` shows one labeled verdict per registered kind; collision behavior unchanged; gate green.

## Notes for next slice
Slice 7 adds `doc-superseded` (predicate `doc_superseded` over a doc path in `request.paths`, deps `docs`) and `missed-gate` (predicate `gate_failed` over covered paths, deps `ci_deploy`) — pure registrations (SignalType + predicates + refutes-pair + query + derive + render + deps + CARD_KINDS entry + verdict_label), plus in-test signals. Multi-verdict already handles them.
