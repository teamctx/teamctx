# Slice 7 — `doc-superseded` + `missed-gate` Card Kinds

> REQUIRED SUB-SKILL: superpowers:subagent-driven-development. Checkbox steps.

**Goal:** Complete the structural card-kind family. Add two more kinds by registration on the multi-kind engine — **doc-superseded** (a doc you rely on was superseded) and **missed-gate** (a required CI gate failed on files you're changing). Both reuse the collision-style path-overlap machinery. In-test signals prove them.

**Architecture:** Each kind = a `SignalType` value + two predicates (`<card>` existential, `<query>` universal) + a `REFUTES_PAIRS` entry + a query constructor + a `_derive_*` + a `render_*` + a `DEPS_REGISTRY` entry + a `CARD_KINDS` entry with a `verdict_label`. After this, `CARD_KINDS` has four kinds and `select_context`/the CLI produce four labeled verdicts automatically.

**Tech Stack:** Python 3.12, pydantic contracts, frozen dataclasses, pytest, ruff, mypy --strict.

---

## File structure
- `contracts.py` — add `"doc_superseded"`, `"missed_gate"` to `SignalType`.
- `prop.py` — register both predicate pairs in `PREDICATE_REGISTRY` + `REFUTES_PAIRS`.
- `select.py` — query constructors, derive fns, render fns, deps entries, `CARD_KINDS` entries.
- `tests/test_select.py` — derive (positive/negative) + four-closure test.

---

## Task 0: Branch + plan
- [ ] `cd /home/eparenti/agents/repos/teamctx && git checkout -b build/slice-07-doc-gate-kinds`
- [ ] `git add docs/superpowers/plans/2026-06-19-slice-07-doc-gate-kinds.md && git commit -m "docs: slice-07 plan (doc-superseded + missed-gate)"`

---

## Task 1: doc-superseded + missed-gate kinds

**Files:** `contracts.py`, `prop.py`, `select.py`, `tests/test_select.py`.

- [ ] **Step 1: Failing tests.** In `tests/test_select.py` add to the `teamctx.core.select` import group: `all_gates_pass_query`, `no_superseded_docs_query`. Reuse the existing in-test `SourceSignal`/`PolicyDecision` imports + the `_criteria_signal` pattern. Append helpers + tests:
```python
def _typed_signal(signal_type: str, source_family: str, scope: dict, sid: str) -> SourceSignal:
    return SourceSignal(
        schema_version="teamctx.source_signal.v0",
        id=sid,
        signal_type=signal_type,
        source_family=source_family,
        scope=scope,
        evidence_summary=f"{signal_type} on {sorted(scope.values(), key=str)}",
        source_display=sid,
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
            decision_reason="metadata allowed as evidence",
        ),
    )


def test_doc_superseded_derives_for_a_relied_on_doc() -> None:
    document = load_document()
    request = document.request_context  # repo auth-service, paths [src/auth/token.py]
    signal = _typed_signal(
        "doc_superseded", "docs", {"repo": "auth-service", "doc": "src/auth/token.py"}, "sig_doc_1"
    )
    claim_cards = derive_claims(request, [signal])
    assert len(claim_cards) == 1
    assert claim_cards[0].claim.predicate == "doc_superseded"
    assert witnesses(claim_cards[0].claim, no_superseded_docs_query(request)) == "refutes"


def test_doc_superseded_ignores_an_unrelated_doc() -> None:
    document = load_document()
    signal = _typed_signal(
        "doc_superseded", "docs", {"repo": "auth-service", "doc": "src/other/x.py"}, "sig_doc_2"
    )
    assert derive_claims(document.request_context, [signal]) == []


def test_missed_gate_derives_for_a_failing_gate_on_a_touched_file() -> None:
    document = load_document()
    request = document.request_context
    signal = _typed_signal(
        "missed_gate", "ci_deploy",
        {"repo": "auth-service", "files": ["src/auth/token.py"]}, "sig_gate_1",
    )
    claim_cards = derive_claims(request, [signal])
    assert len(claim_cards) == 1
    assert claim_cards[0].claim.predicate == "gate_failed"
    assert witnesses(claim_cards[0].claim, all_gates_pass_query(request)) == "refutes"


def test_missed_gate_ignores_a_gate_on_other_files() -> None:
    document = load_document()
    signal = _typed_signal(
        "missed_gate", "ci_deploy", {"repo": "auth-service", "files": ["src/other/x.py"]}, "sig_gate_2"
    )
    assert derive_claims(document.request_context, [signal]) == []


def test_select_context_has_four_closure_entries() -> None:
    document = load_document()
    selection = select_context(
        document.request_context, document.source_signals, document.source_statuses
    )
    assert {e.proposition for e in selection.closure} == {
        "no_pr_conflicts_with_paths",
        "no_criteria_changed_for_issues",
        "no_superseded_docs",
        "all_gates_pass",
    }
```

- [ ] **Step 2: Run** `pytest tests/test_select.py -v` — FAIL (new signal types / query fns missing).

- [ ] **Step 3: Implement.**

`contracts.py`: add `"doc_superseded"` and `"missed_gate"` to `SignalType`.

`prop.py`: `PREDICATE_REGISTRY` += `"doc_superseded": "existential"`, `"no_superseded_docs": "universal"`, `"gate_failed": "existential"`, `"all_gates_pass": "universal"`. `REFUTES_PAIRS` += `("doc_superseded", "no_superseded_docs")` and `("gate_failed", "all_gates_pass")`.

`select.py` — add query constructors (near the others):
```python
def no_superseded_docs_query(request: RequestContext) -> Prop:
    """The universal a doc-superseded card refutes: 'no doc I rely on was superseded'."""

    return Prop(
        predicate="no_superseded_docs",
        subject=SubjectRef(repo=request.repo, paths=tuple(request.paths)),
    )


def all_gates_pass_query(request: RequestContext) -> Prop:
    """The universal a missed-gate card refutes: 'all required gates pass for my change'."""

    return Prop(
        predicate="all_gates_pass",
        subject=SubjectRef(repo=request.repo, paths=tuple(request.paths)),
    )
```
Add derive fns (near `_derive_collision_claim`):
```python
def _derive_doc_superseded_claim(
    request: RequestContext, signal: SourceSignal
) -> ClaimCard | None:
    if signal.scope.get("repo") != request.repo:
        return None
    doc = signal.scope.get("doc")
    if not isinstance(doc, str) or doc not in request.paths:
        return None
    claim = Prop(
        predicate="doc_superseded",
        subject=SubjectRef(repo=request.repo, paths=(doc,)),
        args=(signal.id,),
    )
    return ClaimCard(claim=claim, signal=signal)


def _derive_missed_gate_claim(
    request: RequestContext, signal: SourceSignal
) -> ClaimCard | None:
    if signal.scope.get("repo") != request.repo:
        return None
    covered = signal.scope.get("files")
    covered_list = covered if isinstance(covered, list) else []
    shared = sorted(set(request.paths) & set(covered_list))
    if not shared:
        return None
    claim = Prop(
        predicate="gate_failed",
        subject=SubjectRef(repo=request.repo, paths=tuple(shared)),
        args=(signal.id,),
    )
    return ClaimCard(claim=claim, signal=signal)
```
Add render fns (near `render_collision_claim`):
```python
def render_doc_superseded_claim(claim_card: ClaimCard) -> ContextCard:
    """Render a doc-superseded claim into a human-plane ``ContextCard``."""

    claim = claim_card.claim
    signal = claim_card.signal
    doc = claim.subject.paths[0]
    return ContextCard(
        schema_version="teamctx.context_card.v0",
        id=f"card_{signal.id}",
        section="Verify before relying",
        text=signal.evidence_summary,
        why_this_matters=f"the doc {doc} was superseded; verify it is current before relying.",
        source_display=signal.source_display,
        refs=[signal.id],
        reason=f"a doc you rely on ({doc}) was superseded",
        scope=dict(signal.scope),
        freshness=signal.freshness,
        confidence=signal.confidence,
        source_body="status_only",
        source_open_target_id=None,
        agent_instruction="verify_before_relying",
    )


def render_missed_gate_claim(claim_card: ClaimCard) -> ContextCard:
    """Render a missed-gate claim into a human-plane ``ContextCard``."""

    claim = claim_card.claim
    signal = claim_card.signal
    overlap = ", ".join(claim.subject.paths)
    return ContextCard(
        schema_version="teamctx.context_card.v0",
        id=f"card_{signal.id}",
        section="Needs attention",
        text=signal.evidence_summary,
        why_this_matters=f"a required gate failed on files you are changing: {overlap}.",
        source_display=signal.source_display,
        refs=[signal.id],
        reason=f"a required gate failed on {overlap}",
        scope=dict(signal.scope),
        freshness=signal.freshness,
        confidence=signal.confidence,
        source_body="status_only",
        source_open_target_id=None,
        agent_instruction="verify_before_relying",
    )
```
`DEPS_REGISTRY` += `"no_superseded_docs": frozenset({"docs"})` and `"all_gates_pass": frozenset({"ci_deploy"})`.

`CARD_KINDS` += two entries (define the fns above `CARD_KINDS`):
```python
    CardKind(
        signal_type="doc_superseded",
        card_predicate="doc_superseded",
        verdict_label="Docs check",
        derive=_derive_doc_superseded_claim,
        query=no_superseded_docs_query,
        render=render_doc_superseded_claim,
    ),
    CardKind(
        signal_type="missed_gate",
        card_predicate="gate_failed",
        verdict_label="Gate check",
        derive=_derive_missed_gate_claim,
        query=all_gates_pass_query,
        render=render_missed_gate_claim,
    ),
```

- [ ] **Step 4: Full gate.** `pytest` (collision/criteria tests unchanged; new derive tests pass; four-closure test passes; CLI/render tests unaffected — they don't assert exact closure count). `ruff check src tests`; `mypy src`. If any existing test breaks because closure grew (e.g. one asserting a closure count), generalize it to membership (do NOT weaken collision/criteria assertions) and report it.

- [ ] **Step 5: Commit**
```bash
git add src/teamctx/core/contracts.py src/teamctx/core/prop.py src/teamctx/core/select.py tests/test_select.py
git commit -m "feat: doc-superseded + missed-gate card kinds (structural family complete)"
```

---

## Task 2: Verify
- [ ] `pytest && ruff check src tests && mypy src` green.
- [ ] Purity guard passes.
- [ ] Live smoke (optional): `work-start` against project-foundry now shows four verdict lines (Conflict NOT CLEAR; Criteria/Docs/Gate UNKNOWN — their families unobserved).

**Definition of done:** four registered card kinds (collision, criteria-changed, doc-superseded, missed-gate); each derives from its signal with correct refutes-pair + deps; four labeled verdicts; gate green. The structural card-kind family is complete.

## Notes for next slices
Slice 8 = thin authority (declared `.teamctx` source → `κ.authority` + refuse-to-pick / surface-conflict, pillar S2). Slice 9 = replay/snapshot (T1) + structured `why{reason_code,params}` (#11) + severity decomposition + conformance fixture (#6). The "card says THAT not WHAT" legibility (from the dogfood) can fold into slice 9's structured-why work.
