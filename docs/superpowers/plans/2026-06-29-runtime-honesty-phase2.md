# Runtime-Honesty Carrier (Phase 2) Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Teach the deterministic core to represent two real coverage states it cannot express today, `pending` (a gate whose checks are still running) and `not_applicable` (a docs root scanned but nothing relied-on in scope), and surface them honestly, so neither collapses into a false clear or a false "couldn't reach", while sweeping the unproven word "required" out of gate copy.

**Architecture:** A four-stop carrier already half-exists. `evaluate.py` propagates any `Completeness` string verbatim as `Valuation("unknown", reason)`, and `assess._status_for` maps reasons to a `CheckStatus`, so the new states need NO change to `evaluate.py` or `broker.py`. The work concentrates at the two ends: extend the two core enums + refine `assess_completeness` precedence (a real unreachable dominates pending, which dominates not_applicable), have the gate and docs connectors emit the new statuses, and add render buckets so every status is surfaced exactly once.

**Tech Stack:** Python 3.12, pydantic v2 (frozen contract models), click CLI, pytest. Per-task gate: `python -m pytest -q -p no:cacheprovider && ruff check src tests && python -m mypy src`.

**Source of truth:** spec `docs/superpowers/specs/2026-06-29-onboard-runtime-honesty.md`, sections 1.4 to 1.7. Phase 1 (1.1 to 1.3) is merged at `3ad67c0`. Part 2 (onboard, sections 2.x) is Phase 3, NOT this plan.

**Settled decisions carried in:** additive-within-v0 for the two enum extensions (Task 10 records the changelog note); the "required" claim is removed, not yet proven (real branch-protection requiredness is deferred on merit).

**House rules:** no em dashes anywhere (hard ship gate; grep for the em dash, U+2014, before each commit). Tests must be network-free. Build complete to the bar; do not cut scope.

---

## Revisions (rev 2, after the codex plan-review)

A codex adversarial review (gpt-5.5, xhigh) found one P0 and several P1s, all verified against the
code by the architect-arbiter. Apply these on top of the tasks below; where they conflict, the
revision wins.

**R1 (was P0): the hook must render mixed important statuses, not drop them.** Two holes in the
planned Task 9: (a) conflict `found` + gate `pending` gives `heads_up`, and `_heads_up` rendered only
the finding cards, so the pending gate was silent; (b) conflict `unreachable` + gate `pending` gives
`cant_verify`, and the planned `_cant_verify` saw `important_unreachable` and said "couldn't check
failing checks", which is false (we did check; they are pending). Fix: make the hook total over
important non-clear states. Replace Task 9's hook code with:

```python
# src/teamctx/hook_signal.py
from teamctx.assessment import IMPORTANT_CHECKS, CheckState, WorkStartAssessment, assess

_HOOK_GAP = {"conflict": "open pull requests", "gate": "failing checks"}


def hook_signal(answer: BrokerAnswer, *, file_path: str, token_present: bool) -> str:
    a = assess(answer)
    if a.kind == "heads_up":
        return _heads_up(a, file_path)
    if a.kind == "cant_verify":
        return _cant_verify(a, token_present)
    return _ready(a.checks, file_path)


def _important_gap_notes(a: WorkStartAssessment) -> list[str]:
    # Brief, honest notes for important checks that are unconfirmed (unreachable or pending), so a
    # finding-driven heads_up never hides that the gate or PR check could not be confirmed.
    notes: list[str] = []
    for s in a.checks:
        if s.check not in IMPORTANT_CHECKS:
            continue
        if s.status == "pending":
            notes.append("CI checks are still running, so the gate isn't confirmed green yet.")
        elif s.status == "unreachable":
            notes.append(
                f"teamctx couldn't reach GitHub to check {_HOOK_GAP.get(s.check, s.check)}, "
                "so it's unconfirmed."
            )
    return notes


def _heads_up(a: WorkStartAssessment, file_path: str) -> str:
    lines = [f"teamctx: before you edit {file_path}, from the team's current work:"]
    lines.extend(f"  • {card.text} ({card.why_this_matters})" for card in a.findings)
    lines.extend(f"  • {note}" for note in _important_gap_notes(a))
    lines.append(
        "Factor these into your plan, and surface anything relevant to your human "
        "collaborator so they can decide."
    )
    return "\n".join(lines)


def _cant_verify(a: WorkStartAssessment, token_present: bool) -> str:
    unreachable = [s.check for s in a.checks if s.status == "unreachable" and s.check in IMPORTANT_CHECKS]
    pending = [s.check for s in a.checks if s.status == "pending" and s.check in IMPORTANT_CHECKS]
    parts: list[str] = []
    if unreachable:
        if not token_present:
            parts.append(
                "teamctx couldn't check what else is happening around this file. It doesn't have "
                "access to GitHub yet. To switch that on, set GITHUB_TOKEN in your environment "
                "(or GITHUB_TOKEN_FILE with a path to a token file). If you'd rather not connect "
                "it right now, keep working; you just won't get a heads-up about open pull requests "
                "on the same files or checks that are failing."
            )
        else:
            parts.append(
                "teamctx couldn't reach GitHub just now, so it couldn't check for open pull requests "
                "or failing checks on these files. This is likely a transient connection issue. You "
                "won't get those warnings this session, so glance at GitHub yourself if this file is "
                "sensitive."
            )
    if pending:
        parts.append(
            "teamctx: CI checks on this branch are still running, so it can't confirm the gate is "
            "green yet. If a green build matters for this edit, wait for it or check the run yourself."
        )
    return " ".join(parts)
```

Tests (Task 9) MUST include: conflict found + gate pending (heads_up mentions the pending gate);
conflict unreachable + gate pending (cant_verify mentions BOTH, and does not claim it couldn't check
the gate). Existing heads_up tests that assert exact output and now also have an unreachable/pending
important check need updating; a heads_up with everything else clear is unchanged.

**R2 (was P1): normalize request paths to repo-relative POSIX. NEW TASK, do it BEFORE the docs task.**
`--path ./docs/old.md` reaches `RequestContext.paths` verbatim (`resolve.py:63`, `runner.py:56`), but
connector signal paths are repo-relative POSIX (`docs/old.md`), so the set intersection misses. This
silently breaks docs (now `not_applicable` instead of a real finding), collision, and gate derivation.
Fix at the boundary, reusing the hook's existing logic:
- Promote `hook.py:114 _repo_relative(root, path)` to a public `git_context.repo_relative_path(root,
  path) -> str` (next to `resolve_project_root`); have `hook.py` import it (drop the private copy).
- In `resolve_work_start_inputs` (`resolve.py`), normalize each path via `repo_relative_path(root, p)`
  against the resolved root before constructing `WorkStartInputs`.
- In the dev probes that build a `RequestContext` directly from raw `--path` (`cli.py` docs-probe,
  gate-probe, issue-probe, collision paths), normalize the same way.
- Test: `--path ./docs/old.md` with a superseded `docs/old.md` yields a doc-superseded FINDING (not
  `not_applicable`); and a normalized collision path still matches. Keep the helper's existing fallback
  (a path that cannot be made repo-relative is returned as a clean POSIX string, never crashes).

**R3 (was P1): keep the contract general; make the render total instead of a family-bound validator.**
The two new states are family-bound today (only the gate is `pending`, only docs is `not_applicable`),
but both will plausibly generalize (a slow PR check could be pending; any check could be not applicable),
so binding them to a family in `contracts.py` would be a premature constraint we would soon relax.
Instead, make assessment and render TOTAL over every check x status so no combination drops or KeyErrors.
Revise Task 8's render: use `.get` lookups with a generic fallback, and bullet every important non-clear
check (see R4). No change to Task 1 (the enum extension stays as written; do NOT add a validator).

**R4 (was P1 + P2): render totality (revise Task 8).** Replace the phrase tables and bullet logic so
they cover any check, and surface every non-clear status exactly once:

```python
# src/teamctx/contract_render.py
_PENDING_PHRASE: dict[CheckId, str] = {
    "gate": "failing checks (CI still running, not confirmed green yet)",
}
_NOT_APPLICABLE_PHRASE: dict[CheckId, str] = {
    "docs": "docs (a docs root is set, but none of the files in scope are docs you rely on)",
}


def _pending_phrase(check: CheckId) -> str:
    return _PENDING_PHRASE.get(check, f"{check} (still running, not confirmed yet)")


def _not_applicable_phrase(check: CheckId) -> str:
    return _NOT_APPLICABLE_PHRASE.get(check, f"{check} (not applicable to the files in scope)")


def _pending_bullet(check: CheckId) -> str:
    if check == "gate":
        return ("  • Failing checks: CI checks are still running, so the gate isn't confirmed green "
                "yet. Wait for the build or check the run before relying on a green gate.")
    return f"  • {check}: still running, not confirmed yet."


def _cant_verify_bullets(assessment: WorkStartAssessment) -> list[str]:
    status = {s.check: s.status for s in assessment.checks}
    conflict_unreachable = status.get("conflict") == "unreachable"
    gate_unreachable = status.get("gate") == "unreachable"
    fix = (
        "teamctx couldn't reach GitHub. Either it has no access yet (set GITHUB_TOKEN, or "
        "GITHUB_TOKEN_FILE with a path to a token file) or it's a temporary connection issue."
    )
    bullets: list[str] = []
    if conflict_unreachable and gate_unreachable:
        bullets.append(f"  • Open PRs and failing checks: {fix} Until it's back you won't see "
                       "colliding PRs or red CI on your files.")
    elif conflict_unreachable:
        bullets.append(f"  • Open PRs: {fix} Until it's back you won't see colliding PRs on your files.")
    elif gate_unreachable:
        bullets.append(f"  • Failing checks: {fix} Until it's back you won't see red CI on your files.")
    for s in assessment.checks:
        if s.status == "pending" and s.check in IMPORTANT_CHECKS:
            bullets.append(_pending_bullet(s.check))
    return bullets


def _still_running_line(assessment: WorkStartAssessment) -> str:
    # An important pending check is already bulleted in cant_verify; surface the rest here so a
    # pending check is never dropped when a found elsewhere made the kind heads_up.
    in_bullets = assessment.kind == "cant_verify"
    gaps = [
        _pending_phrase(s.check)
        for s in assessment.checks
        if s.status == "pending" and not (in_bullets and s.check in IMPORTANT_CHECKS)
    ]
    if not gaps:
        return ""
    return "  Still running: " + "; ".join(gaps) + "."


def _not_applicable_line(assessment: WorkStartAssessment) -> str:
    gaps = [_not_applicable_phrase(s.check) for s in assessment.checks if s.status == "not_applicable"]
    if not gaps:
        return ""
    return "  Not applicable: " + "; ".join(gaps) + "."
```

Add Task 8 tests for the mixed cases: conflict found + gate pending (heads_up still surfaces "Still
running"); conflict unreachable + gate pending (cant_verify shows the unreachable bullet AND the pending
bullet); conflict found + docs not_applicable (a "Not applicable" line plus the finding).

**R5 (was P1): close the malformed-payload false-clear in the gate probe (revise Task 4).** A payload
`{"check_runs": null}` with no `total_count` yields failing `[]`, truncated `False`, pending `False`,
then `fresh` (a false clear). In `fetch_failing_check_runs`, after `payload = get_json(...)`, validate
the shape: if `payload` is not a dict, or `payload["check_runs"]` is present but not a list, raise
`GitHubProbeError`, which the probe already routes to `unavailable_gates_document`. Add a malformed
payload test asserting `unavailable`, not `fresh`.

**R6 (was P1): update every `CheckRunsFetch(...)` caller in Task 4.** Adding the required `pending`
field breaks three test call sites: `tests/test_gate_probe_cli.py:12`, `tests/test_why_open_source_cli
.py:49`, `tests/test_work_start_cli.py:61`. Add `pending=False` to each in the same task so it lands
green.

**R7 (was P1): the copy sweep missed README (revise Task 7).** "CI is green" also appears at
`README.md:66` and `README.md:75` (example outputs). Change both to "no failing checks found". The
many `required=True` click options are real option requirements, not the gate claim; leave them.

**R8 (was P2): stage exact files in Task 7**, not `git add -A`, so unrelated local changes are not
swept in.

---

## File map (what changes and why)

Core (pure, no I/O):
- `src/teamctx/core/contracts.py:52` ` SourceStatusValue` gains `pending`, `not_applicable`.
- `src/teamctx/core/select.py:377` `Completeness` gains `incomplete[pending]`, `not_applicable[out-of-scope]`; `assess_completeness` (`:408`) gets worst-status precedence.

Assessment (pure):
- `src/teamctx/assessment.py` `CheckStatus` (`:18`) gains `pending`, `not_applicable`; `_status_for` (`:48`) maps the two new reasons; kind precedence (`:85`) treats a pending IMPORTANT check as `cant_verify`.

Connectors (emit the new statuses):
- `src/teamctx/connectors/github_checks.py` parse incomplete runs; probe emits `pending` when incomplete runs exist and none fail (found-over-pending).
- `src/teamctx/connectors/gate_status.py` new `pending_gates_document`; drop "Required" from the evidence string.
- `src/teamctx/connectors/docs_supersession.py` `normalize_superseded_docs` gains a required `relied_on_doc_in_scope` flag; emits `not_applicable` when False.
- `src/teamctx/connectors/docs.py` the probe computes the in-scope flag from scanned paths and passes it.

Render (speak the states; surface each exactly once):
- `src/teamctx/contract_render.py` generalize the `cant_verify` headline; pending bullet + a `Still running:` line; a `Not applicable:` line.
- `src/teamctx/hook_signal.py` the `cant_verify` branch distinguishes a pending gate from an unreachable source; `not_applicable` stays unheadlined.

Copy sweep + config:
- `src/teamctx/core/select.py:86,273,274`, `gate_status.py:66`, `mcp_server.py:28`, `README.md:24`: drop "required" from gate copy. `contract_render.py:27`, `hook_signal.py:17`: "CI is green" becomes "no failing checks found".
- `src/teamctx/cli.py:93` `init` stops auto-enabling `docs_root`; the now-dead `_detect_docs_root` (`:695`) is removed.

Docs:
- `CHANGELOG.md` additive-within-v0 note for the two enum extensions.

---

## Task 1: Extend `SourceStatusValue` (core contract)

**Files:**
- Modify: `src/teamctx/core/contracts.py:52`
- Test: `tests/test_core_contracts.py`

- [ ] **Step 1: Write the failing test**

```python
# tests/test_core_contracts.py
import pytest
from teamctx.connectors._contract import source_status


@pytest.mark.parametrize("status", ["pending", "not_applicable"])
def test_source_status_accepts_new_coverage_states(status: str) -> None:
    s = source_status(
        source_id="github_check_runs",
        source_family="ci_deploy",
        scope={"repo": "o/n"},
        status=status,  # type: ignore[arg-type]
        observed_at="2026-06-29T00:00:00Z",
        safe_user_message="probe ran; not a clear and not unreachable.",
        visibility="warning_when_relevant",
        policy_reason="metadata only.",
    )
    assert s.status == status
    # the new states are NOT unhealthy, so last_checked_at is recorded (we did observe).
    assert s.last_checked_at == "2026-06-29T00:00:00Z"
```

- [ ] **Step 2: Run test to verify it fails**

Run: `python -m pytest tests/test_core_contracts.py::test_source_status_accepts_new_coverage_states -v`
Expected: FAIL with a pydantic validation error (`status` not a permitted literal).

- [ ] **Step 3: Write minimal implementation**

In `src/teamctx/core/contracts.py:52`, change:

```python
SourceStatusValue = Literal["fresh", "stale", "unavailable", "blocked", "disabled"]
```

to:

```python
SourceStatusValue = Literal[
    "fresh", "stale", "unavailable", "blocked", "disabled", "pending", "not_applicable"
]
```

Leave the `SourceStatus` fail-closed validators (`:142-150`) unchanged: `pending` and `not_applicable` are not in the unhealthy set `{blocked, unavailable, disabled}`, and connectors emit them with a metadata-only policy (`can_include_source_text=False`), so no new validator rule is needed.

- [ ] **Step 4: Run test to verify it passes**

Run: `python -m pytest tests/test_core_contracts.py -v`
Expected: PASS.

- [ ] **Step 5: Commit**

```bash
git add src/teamctx/core/contracts.py tests/test_core_contracts.py
git commit -m "feat(core): SourceStatusValue gains pending and not_applicable"
```

---

## Task 2: Extend `Completeness` and refine `assess_completeness`

This is the heart of the carrier. The current code collapses every non-fresh status to `incomplete[stale-dep]` and short-circuits to `incomplete[policy-gap]` on an absent mandated family. The new version keeps policy-gap dominant (an entirely absent mandated source is the most severe coverage hole), then classifies the present families by their worst status with precedence: stale-ish > pending > not_applicable > complete. "Stale-ish" is defined as any status other than `fresh`, `pending`, or `not_applicable`, so an unrecognized or unhealthy status still fails conservatively to `incomplete[stale-dep]`, preserving today's "non-fresh means stale-dep" default.

**Files:**
- Modify: `src/teamctx/core/select.py:377` (the `Completeness` literal) and `:408-430` (`assess_completeness`)
- Test: `tests/test_select.py`

- [ ] **Step 1: Write the failing tests**

```python
# tests/test_select.py  (add these)
from teamctx.core.select import (
    Coverage,
    CoverageEntry,
    all_gates_pass_query,
    assess_completeness,
    no_superseded_docs_query,
)
from teamctx.core.contracts import RequestContext


def _req() -> RequestContext:
    return RequestContext(
        schema_version="teamctx.request_context.v0",
        request_id="r1",
        repo="o/n",
        task="t",
        paths=["a.py"],
        requested_at="2026-06-29T00:00:00Z",
    )


def _cov(*statuses: tuple[str, str]) -> Coverage:
    return Coverage(
        entries=tuple(
            CoverageEntry(source_id=f"s{i}", source_family=fam, status=st, last_checked_at=None)
            for i, (fam, st) in enumerate(statuses)
        )
    )


def test_assess_completeness_pending_when_gate_pending_and_nothing_worse() -> None:
    q = all_gates_pass_query(_req())
    assert assess_completeness(q, _cov(("ci_deploy", "pending"))) == "incomplete[pending]"


def test_assess_completeness_not_applicable_when_only_docs_out_of_scope() -> None:
    q = no_superseded_docs_query(_req())
    assert (
        assess_completeness(q, _cov(("docs", "not_applicable")))
        == "not_applicable[out-of-scope]"
    )


def test_assess_completeness_stale_dominates_pending() -> None:
    # a real unreachable beats pending within the same family.
    q = all_gates_pass_query(_req())
    cov = _cov(("ci_deploy", "unavailable"), ("ci_deploy", "pending"))
    assert assess_completeness(q, cov) == "incomplete[stale-dep]"


def test_assess_completeness_fresh_is_complete() -> None:
    q = all_gates_pass_query(_req())
    assert assess_completeness(q, _cov(("ci_deploy", "fresh"))) == "complete"


def test_assess_completeness_absent_family_is_policy_gap() -> None:
    q = all_gates_pass_query(_req())
    assert assess_completeness(q, _cov()) == "incomplete[policy-gap]"
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `python -m pytest tests/test_select.py -k assess_completeness -v`
Expected: the pending and not_applicable cases FAIL (current code returns `incomplete[stale-dep]` for both); the stale/fresh/absent cases pass.

- [ ] **Step 3: Write the implementation**

In `src/teamctx/core/select.py`, extend the literal at `:377`:

```python
Completeness = Literal[
    "complete",
    "incomplete[dangling]",
    "incomplete[stale-dep]",
    "incomplete[pending]",
    "incomplete[policy-gap]",
    "incomplete[unbounded]",
    "incomplete[unmodeled-ref]",
    "not_applicable[out-of-scope]",
]
```

Replace `assess_completeness` (`:408-430`) with:

```python
def assess_completeness(prop: Prop, coverage: Coverage) -> Completeness:
    """The paper's ``complete?``: is every mandated dependency of ``prop`` observed fresh?

    Precedence: an absent mandated family is ``incomplete[policy-gap]`` (we never looked).
    Among present families, the worst status wins: any stale/unavailable/blocked/disabled (or
    any unrecognized status) gives ``incomplete[stale-dep]`` (a real unreachable dominates),
    then ``pending`` gives ``incomplete[pending]``, then a family whose only non-fresh status is
    ``not_applicable`` gives ``not_applicable[out-of-scope]``, else ``complete``. The reasons
    ``dangling``/``unbounded``/``unmodeled-ref`` are defined but not yet emitted.
    """

    entries_by_family: dict[str, list[CoverageEntry]] = {}
    for entry in coverage.entries:
        entries_by_family.setdefault(entry.source_family, []).append(entry)

    statuses: list[str] = []
    for family in sorted(deps_for(prop)):
        family_entries = entries_by_family.get(family, [])
        if not family_entries:
            return "incomplete[policy-gap]"
        statuses.extend(entry.status for entry in family_entries)

    if any(status not in {"fresh", "pending", "not_applicable"} for status in statuses):
        return "incomplete[stale-dep]"
    if any(status == "pending" for status in statuses):
        return "incomplete[pending]"
    if any(status == "not_applicable" for status in statuses):
        return "not_applicable[out-of-scope]"
    return "complete"
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `python -m pytest tests/test_select.py -v`
Expected: PASS (including the pre-existing select tests; the fresh/stale/absent behavior is unchanged).

- [ ] **Step 5: Commit**

```bash
git add src/teamctx/core/select.py tests/test_select.py
git commit -m "feat(core): assess_completeness carries pending and not_applicable[out-of-scope]"
```

---

## Task 3: Map the new reasons in assessment + kind precedence

`evaluate.py` already turns a non-complete completeness into `Valuation("unknown", reason)` (`evaluate.py:57`), so the two new reasons reach `_status_for` with no change to `evaluate.py` or `broker.py`. We map them and extend the kind rule so a pending IMPORTANT check reads `cant_verify`.

**Files:**
- Modify: `src/teamctx/assessment.py:18` (`CheckStatus`), `:48-57` (`_status_for`), `:85` (kind precedence)
- Test: `tests/test_assessment.py`, and a guard in `tests/test_evaluate.py`

- [ ] **Step 1: Write the failing tests**

```python
# tests/test_evaluate.py  (add: lock the no-change propagation claim)
from teamctx.core.evaluate import evaluate
from teamctx.core.select import ClosureEntry
from teamctx.core.prop import Prop, SubjectRef


def _universal(pred: str) -> Prop:
    return Prop(predicate=pred, subject=SubjectRef(repo="o/n", paths=()))


def test_evaluate_propagates_pending_reason_verbatim() -> None:
    q = _universal("all_gates_pass")
    closure = (ClosureEntry(proposition="all_gates_pass", status="incomplete[pending]"),)
    v = evaluate(q, (), closure)
    assert v.value == "unknown"
    assert v.reason == "incomplete[pending]"


def test_evaluate_propagates_not_applicable_reason_verbatim() -> None:
    q = _universal("no_superseded_docs")
    closure = (ClosureEntry(proposition="no_superseded_docs", status="not_applicable[out-of-scope]"),)
    v = evaluate(q, (), closure)
    assert v.value == "unknown"
    assert v.reason == "not_applicable[out-of-scope]"
```

```python
# tests/test_assessment.py  (add)
from teamctx.assessment import _status_for
from teamctx.core.evaluate import Valuation


def test_status_for_maps_pending() -> None:
    assert _status_for(Valuation("unknown", "incomplete[pending]")) == "pending"


def test_status_for_maps_not_applicable() -> None:
    assert _status_for(Valuation("unknown", "not_applicable[out-of-scope]")) == "not_applicable"
```

For the kind precedence, add an end-to-end assessment test driven through `broker_answer` with a pending gate. A pending gate means: a `ci_deploy` source status of `pending`, no missed_gate signal, request paths present. Build it via the gate connector helper (available after Task 4) OR directly with `pending_gates_document`; to keep Task 3 self-contained, construct the document inline here:

```python
# tests/test_assessment.py  (add)
from teamctx.assessment import assess
from teamctx.connectors._contract import source_status
from teamctx.core.broker import broker_answer
from teamctx.core.contracts import CoreContractDocument, RequestContext, SourceStatus


def _req_paths() -> RequestContext:
    return RequestContext(
        schema_version="teamctx.request_context.v0",
        request_id="r1", repo="o/n", task="t", paths=["a.py"],
        requested_at="2026-06-29T00:00:00Z",
    )


def _pending_gate_status() -> SourceStatus:
    return source_status(
        source_id="github_check_runs", source_family="ci_deploy", scope={"repo": "o/n"},
        status="pending", observed_at="2026-06-29T00:00:00Z",
        safe_user_message="CI checks are still running; not confirmed green yet.",
        visibility="warning_when_relevant", policy_reason="metadata only.",
    )


def test_pending_gate_makes_kind_cant_verify() -> None:
    req = _req_paths()
    answer = broker_answer(req, signals=(), statuses=(_pending_gate_status(),))
    a = assess(answer)
    gate = next(s for s in a.checks if s.check == "gate")
    assert gate.status == "pending"
    assert a.kind == "cant_verify"
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `python -m pytest tests/test_evaluate.py tests/test_assessment.py -v`
Expected: the evaluate tests PASS already (propagation is generic); the `_status_for` and kind tests FAIL (`_status_for` returns `not_configured`; kind returns `ready`).

Note: if the evaluate tests fail to import `ClosureEntry`/`status` literal, that means Task 2 was skipped; Task 2 must land first.

- [ ] **Step 3: Write the implementation**

In `src/teamctx/assessment.py`, extend `CheckStatus` (`:18`):

```python
CheckStatus = Literal["clear", "found", "unreachable", "not_configured", "pending", "not_applicable"]
```

Extend `_status_for` (`:48`), inserting the two mappings before the final fallthrough:

```python
def _status_for(valuation: Valuation) -> CheckStatus:
    if valuation.value == "true":
        return "clear"
    if valuation.value == "false":
        return "found"
    if valuation.reason == "conflicting-evidence":
        return "found"  # connectors fired and disagree: a finding, not a config gap
    if valuation.reason == "incomplete[stale-dep]":
        return "unreachable"
    if valuation.reason == "incomplete[pending]":
        return "pending"
    if valuation.reason == "not_applicable[out-of-scope]":
        return "not_applicable"
    return "not_configured"
```

Extend the kind precedence (`:85`) so a pending IMPORTANT check is `cant_verify`:

```python
    if any(s.status == "found" for s in states):
        kind = "heads_up"
    elif any(
        s.status in {"unreachable", "pending"} and s.check in IMPORTANT_CHECKS for s in states
    ):
        kind = "cant_verify"
    else:
        kind = "ready"
```

`not_applicable` is a non-IMPORTANT docs state, so like `not_configured` it never changes the kind and never blocks `ready`. Found-over-pending (Task 4) guarantees a failing run is `found`, so `pending` only reaches this rule when there is no failure.

- [ ] **Step 4: Run tests to verify they pass**

Run: `python -m pytest tests/test_evaluate.py tests/test_assessment.py -v`
Expected: PASS.

- [ ] **Step 5: Commit**

```bash
git add src/teamctx/assessment.py tests/test_assessment.py tests/test_evaluate.py
git commit -m "feat: assessment maps pending/not_applicable; pending IMPORTANT check is cant_verify"
```

---

## Task 4: Gate connector emits `pending` for in-progress runs

Today `parse_failing_check_runs` skips any run whose `status != "completed"` (`github_checks.py:117`), so a branch mid-build reads green. New behavior: detect incomplete runs; when there are incomplete runs and none failing (and the page is not truncated), emit a `pending` gate status. Precedence in the probe: found (failing gates) > truncated (stale) > pending > fresh.

**Files:**
- Modify: `src/teamctx/connectors/github_checks.py` (`CheckRunsFetch`, `fetch_failing_check_runs`, `run_github_checks_probe`, new `parse_incomplete_check_runs`)
- Modify: `src/teamctx/connectors/gate_status.py` (new `pending_gates_document`)
- Test: `tests/test_gate_status.py`, `tests/test_github_checks_truncation.py`

- [ ] **Step 1: Write the failing tests**

```python
# tests/test_gate_status.py  (add)
from teamctx.connectors.gate_status import pending_gates_document
from teamctx.connectors.github_checks import parse_incomplete_check_runs


def test_parse_incomplete_runs_true_when_in_progress_present() -> None:
    payload = {"check_runs": [
        {"name": "ruff", "status": "completed", "conclusion": "success", "html_url": "u"},
        {"name": "mypy", "status": "in_progress", "conclusion": None, "html_url": "u2"},
    ]}
    assert parse_incomplete_check_runs(payload) is True


def test_parse_incomplete_runs_false_when_all_completed() -> None:
    payload = {"check_runs": [
        {"name": "ruff", "status": "completed", "conclusion": "success", "html_url": "u"},
    ]}
    assert parse_incomplete_check_runs(payload) is False


def test_pending_gates_document_status_only_no_signals(req_context) -> None:
    doc = pending_gates_document(
        req_context, repo="o/n", observed_at="2026-06-29T00:00:00Z",
        safe_user_message="CI checks are still running; not confirmed green yet.",
    )
    assert doc.source_signals == []
    assert doc.source_statuses[0].status == "pending"
    assert doc.source_statuses[0].source_family == "ci_deploy"
```

```python
# tests/test_github_checks_truncation.py  (add; mirror the existing opener-mock style there)
from teamctx.connectors.github_checks import run_github_checks_probe


def test_probe_emits_pending_when_only_in_progress(req_context) -> None:
    payload = {"total_count": 1, "check_runs": [
        {"name": "mypy", "status": "in_progress", "conclusion": None, "html_url": "u"},
    ]}
    opener = _opener_returning(payload)  # reuse this file's existing opener helper
    doc = run_github_checks_probe(
        repo="o/n", ref="main", token="t", request_context=req_context,
        observed_at="2026-06-29T00:00:00Z", opener=opener,
    )
    assert doc.source_signals == []
    assert doc.source_statuses[0].status == "pending"


def test_probe_found_dominates_pending(req_context) -> None:
    payload = {"total_count": 2, "check_runs": [
        {"name": "pytest", "status": "completed", "conclusion": "failure", "html_url": "u1"},
        {"name": "mypy", "status": "in_progress", "conclusion": None, "html_url": "u2"},
    ]}
    opener = _opener_returning(payload)
    doc = run_github_checks_probe(
        repo="o/n", ref="main", token="t", request_context=req_context,
        observed_at="2026-06-29T00:00:00Z", opener=opener,
    )
    # the failing run wins: a missed_gate signal, fresh status, no pending.
    assert any(sig.signal_type == "missed_gate" for sig in doc.source_signals)
    assert doc.source_statuses[0].status == "fresh"
```

Note for the executor: `req_context` and the opener helper (`_opener_returning` / equivalent) already exist in these test modules or `conftest.py`; reuse them rather than re-defining. If `req_context` is local to one module, lift it to a fixture or inline a `RequestContext` with `paths=["a.py"]`. Confirm the exact helper name with `grep -n "def _opener\|req_context\|opener" tests/test_github_checks_truncation.py tests/conftest.py` before writing.

- [ ] **Step 2: Run tests to verify they fail**

Run: `python -m pytest tests/test_gate_status.py tests/test_github_checks_truncation.py -v`
Expected: the new tests FAIL (`parse_incomplete_check_runs` and `pending_gates_document` do not exist; the probe emits `fresh` for in-progress-only).

- [ ] **Step 3: Write the implementation**

In `src/teamctx/connectors/gate_status.py`, add after `normalize_failing_gates` (uses the existing `source_status` import):

```python
def pending_gates_document(
    request_context: RequestContext,
    *,
    repo: str,
    observed_at: str,
    source_id: str = "github_check_runs",
    safe_user_message: str,
) -> CoreContractDocument:
    """A document carrying a single ``pending`` gate status: checks are still running, so this
    is neither a clear nor an unreachable source. The core carries ``pending`` to a render that
    says the gate is not confirmed green yet."""

    return CoreContractDocument(
        schema_version="teamctx.core_contract_document.v0",
        request_context=request_context,
        source_signals=[],
        source_statuses=[
            source_status(
                source_id=source_id,
                source_family=_SOURCE_FAMILY,
                scope={"repo": request_context.repo},
                status="pending",
                observed_at=observed_at,
                safe_user_message=safe_user_message,
                visibility="warning_when_relevant",
                policy_reason=_POLICY_REASON,
            )
        ],
        source_open_targets=[],
        guidance_records=[],
        session_context_uses=[],
        context_cards=[],
    )
```

In `src/teamctx/connectors/github_checks.py`:

Add `pending: bool` to `CheckRunsFetch` (`:36-37`):

```python
@dataclass(frozen=True)
class CheckRunsFetch:
    failing: list[tuple[str, str]]
    truncated: bool
    pending: bool
```

Add the parser (after `parse_failing_check_runs`):

```python
def parse_incomplete_check_runs(payload: object) -> bool:
    """True when any check-run is still queued or in progress (status != 'completed').

    These runs are not failing (no conclusion yet) but mean the gate cannot be asserted green.
    """

    if not isinstance(payload, dict):
        return False
    runs = payload.get("check_runs")
    if not isinstance(runs, list):
        return False
    return any(isinstance(run, dict) and run.get("status") != "completed" for run in runs)
```

Set it in `fetch_failing_check_runs` (`:86-88`):

```python
    payload = get_json(url, token=token, opener=opener)
    failing = parse_failing_check_runs(payload)
    truncated = _detect_truncation(payload)
    pending = parse_incomplete_check_runs(payload)
    return CheckRunsFetch(failing=failing, truncated=truncated, pending=pending)
```

Add the import for the new helper at the top of `github_checks.py` (the `from teamctx.connectors.gate_status import (...)` block):

```python
from teamctx.connectors.gate_status import (
    FailingGate,
    normalize_failing_gates,
    pending_gates_document,
    unavailable_gates_document,
)
```

Apply the precedence in `run_github_checks_probe` (replace the tail `:65-74`):

```python
    gates = [
        FailingGate(repo=repo, gate_name=name, url=url, files=tuple(request_context.paths))
        for name, url in fetch.failing
    ]
    if not gates and not fetch.truncated and fetch.pending:
        return pending_gates_document(
            request_context,
            repo=repo,
            observed_at=observed_at,
            safe_user_message="CI checks are still running; the gate is not confirmed green yet.",
        )
    return normalize_failing_gates(
        request_context,
        gates,
        observed_at=observed_at,
        coverage_truncated=fetch.truncated,
    )
```

This preserves found-over-pending (failing gates short-circuit to the signal path) and truncation-over-pending (a truncated page stays `stale`, the existing honest-UNKNOWN path).

- [ ] **Step 4: Run tests to verify they pass**

Run: `python -m pytest tests/test_gate_status.py tests/test_github_checks_truncation.py -v`
Expected: PASS. Also run the existing in-progress test referenced by the spec (`tests/test_gate_status.py` around the `in_progress` payload) and update it: a payload with a failing run plus an in_progress run still yields the failing gate; a payload with ONLY an in_progress run now yields `pending` (was `fresh`).

- [ ] **Step 5: Commit**

```bash
git add src/teamctx/connectors/github_checks.py src/teamctx/connectors/gate_status.py tests/test_gate_status.py tests/test_github_checks_truncation.py
git commit -m "feat(connectors): gate emits pending for in-progress runs (found-over-pending)"
```

---

## Task 5: Docs connector emits `not_applicable` when out of scope

Today `normalize_superseded_docs` hard-codes `status="fresh"` (`docs_supersession.py:81`), so a docs root with nothing relied-on in scope reads "current". The probe must compute whether any scanned doc is in `request.paths` and pass it through; the normalizer then emits `fresh` versus `not_applicable`.

**Files:**
- Modify: `src/teamctx/connectors/docs_supersession.py` (`normalize_superseded_docs` signature + status)
- Modify: `src/teamctx/connectors/docs.py` (`run_docs_supersession_probe` computes the flag)
- Test: `tests/test_docs_supersession.py`, `tests/test_docs_probe_cli.py`

- [ ] **Step 1: Write the failing tests**

```python
# tests/test_docs_supersession.py  (add; update any existing direct callers to pass the kwarg)
from teamctx.connectors.docs_supersession import normalize_superseded_docs


def test_normalize_emits_not_applicable_when_no_relied_on_doc_in_scope(req_context) -> None:
    doc = normalize_superseded_docs(
        req_context, [], observed_at="2026-06-29T00:00:00Z", relied_on_doc_in_scope=False
    )
    assert doc.source_statuses[0].status == "not_applicable"


def test_normalize_emits_fresh_when_relied_on_doc_in_scope(req_context) -> None:
    doc = normalize_superseded_docs(
        req_context, [], observed_at="2026-06-29T00:00:00Z", relied_on_doc_in_scope=True
    )
    assert doc.source_statuses[0].status == "fresh"
```

```python
# tests/test_docs_probe_cli.py  (add a probe-level test; reuse the module's reader-injection style)
from teamctx.connectors.docs import run_docs_supersession_probe
from teamctx.core.contracts import RequestContext


def _req(paths: list[str]) -> RequestContext:
    return RequestContext(
        schema_version="teamctx.request_context.v0", request_id="r", repo="o/n", task="t",
        paths=paths, requested_at="2026-06-29T00:00:00Z",
    )


def test_probe_not_applicable_when_scanned_docs_not_in_scope() -> None:
    reader = lambda root: [("docs/guide.md", "---\ntitle: x\n---\nbody")]
    doc = run_docs_supersession_probe(
        repo="o/n", root="docs", request_context=_req(["src/a.py"]),
        observed_at="2026-06-29T00:00:00Z", reader=reader,
    )
    assert doc.source_statuses[0].status == "not_applicable"


def test_probe_fresh_when_scanned_doc_is_in_scope() -> None:
    reader = lambda root: [("docs/guide.md", "---\ntitle: x\n---\nbody")]
    doc = run_docs_supersession_probe(
        repo="o/n", root="docs", request_context=_req(["docs/guide.md"]),
        observed_at="2026-06-29T00:00:00Z", reader=reader,
    )
    assert doc.source_statuses[0].status == "fresh"
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `python -m pytest tests/test_docs_supersession.py tests/test_docs_probe_cli.py -v`
Expected: FAIL (`normalize_superseded_docs` has no `relied_on_doc_in_scope` parameter; the probe always emits `fresh`).

- [ ] **Step 3: Write the implementation**

In `src/teamctx/connectors/docs_supersession.py`, change the `normalize_superseded_docs` signature to add a required keyword-only flag, and compute the status from it (replace `:43-50` signature and the `source_statuses` block `:76-87`):

```python
def normalize_superseded_docs(
    request_context: RequestContext,
    docs: Iterable[SupersededDoc],
    *,
    observed_at: str,
    relied_on_doc_in_scope: bool,
    expires_at: str = "next_refresh",
    source_id: str = "docs_supersession",
) -> CoreContractDocument:
```

```python
    status: SourceStatusValue = "fresh" if relied_on_doc_in_scope else "not_applicable"
    safe_user_message = (
        "Docs supersession metadata refreshed."
        if relied_on_doc_in_scope
        else "A docs root is set, but none of the files in scope are docs you rely on."
    )
    source_statuses = [
        source_status(
            source_id=source_id,
            source_family=_SOURCE_FAMILY,
            scope={"repo": request_context.repo},
            status=status,
            observed_at=observed_at,
            safe_user_message=safe_user_message,
            visibility="silent",
            policy_reason=_POLICY_REASON,
        )
    ]
```

The flag is required (no default) on purpose: a default would re-introduce the silent "assume fresh" we are removing. Every caller must state whether a relied-on doc was in scope.

In `src/teamctx/connectors/docs.py`, compute the flag in `run_docs_supersession_probe` (replace `:60-61`):

```python
    superseded = parse_superseded_docs(repo=repo, files=files)
    scanned_paths = {rel_path for rel_path, _ in files}
    relied_on_in_scope = bool(scanned_paths & set(request_context.paths))
    return normalize_superseded_docs(
        request_context,
        superseded,
        observed_at=observed_at,
        relied_on_doc_in_scope=relied_on_in_scope,
    )
```

`files` is already a concrete list (line 50/52), so iterating it for `scanned_paths` and then passing it to `parse_superseded_docs` is safe. Scanned rel-paths and `request_context.paths` are both repo-relative POSIX, so a set intersection is apples-to-apples.

- [ ] **Step 4: Run tests to verify they pass**

Run: `python -m pytest tests/test_docs_supersession.py tests/test_docs_probe_cli.py -v`
Expected: PASS. Update any pre-existing direct callers of `normalize_superseded_docs` in these test files to pass `relied_on_doc_in_scope=...` (grep first: `grep -rn "normalize_superseded_docs" tests/`).

- [ ] **Step 5: Commit**

```bash
git add src/teamctx/connectors/docs_supersession.py src/teamctx/connectors/docs.py tests/test_docs_supersession.py tests/test_docs_probe_cli.py
git commit -m "feat(connectors): docs emits not_applicable when no relied-on doc is in scope"
```

---

## Task 6: `init` stops auto-enabling `docs_root`

Auto-detecting `docs_root` from the presence of a `docs/` folder turns docs into a check the user never asked for, which (before Task 5) read as a false "current". Drop the auto-detect: only an explicit `--docs-root` enables it.

**Files:**
- Modify: `src/teamctx/cli.py:93` (drop the `_detect_docs_root` fallback) and remove the now-dead `_detect_docs_root` (`:695`); fix the `init` help/docstring that promises auto-detect.
- Test: `tests/test_init_command.py` (the auto-detect cases flip)

- [ ] **Step 1: Update the failing tests**

In `tests/test_init_command.py`:
- Rewrite `test_init_detects_docs_root_when_docs_dir_exists` (`:84`) to assert the opposite: with a `docs/` dir present but no `--docs-root`, the written config has NO `docs_root`.

```python
def test_init_does_not_auto_enable_docs_root_when_docs_dir_exists(
    runner, tmp_path, _git_repo_with_origin
) -> None:
    (tmp_path / "docs").mkdir()
    result = runner.invoke(init_command, ["--repo", "o/n"], obj=None)
    assert result.exit_code == 0
    assert _config_at(tmp_path)["work_start"].get("docs_root") is None
    assert "Docs root: not set" in result.output
```

- Keep `test_init_docs_root_flag_overrides_detection` (`:123`) but it now just asserts `--docs-root docs` sets `docs_root == "docs"` (there is no detection to override; rename to `test_init_docs_root_set_only_by_flag`).
- Update the module docstring (`:4`) so it no longer says init "auto-detects docs_root".

Adjust the exact fixture/argument names to match the file (grep `def test_init_detects_docs_root` and the surrounding fixtures first).

- [ ] **Step 2: Run tests to verify they fail**

Run: `python -m pytest tests/test_init_command.py -v`
Expected: the rewritten case FAILS (current init auto-detects, so `docs_root == "docs"`).

- [ ] **Step 3: Write the implementation**

In `src/teamctx/cli.py`, change `:93`:

```python
    resolved_docs_root = docs_root if docs_root is not None else _detect_docs_root(root)
```

to:

```python
    resolved_docs_root = docs_root
```

Delete the now-unused `_detect_docs_root` function (`:695`). Confirm it is dead first:

```bash
grep -rn "_detect_docs_root" src tests
```

Expected after deletion: no references. Update the `init_command` help text / docstring that mentions auto-detecting a docs root so it states only that `--docs-root` enables docs.

- [ ] **Step 4: Run tests to verify they pass**

Run: `python -m pytest tests/test_init_command.py -v && ruff check src`
Expected: PASS, and ruff clean (no unused function).

- [ ] **Step 5: Commit**

```bash
git add src/teamctx/cli.py tests/test_init_command.py
git commit -m "feat(cli): init no longer auto-enables docs_root (explicit --docs-root only)"
```

---

## Task 7: Sweep "required" from gate copy; "CI is green" becomes "no failing checks found"

Copy-only honesty pass. We report failing checks; we do not assert they are required (real requiredness is deferred). And the clear phrase stops over-claiming a green build.

**Files:**
- Modify: `src/teamctx/core/select.py:86,273,274`, `src/teamctx/connectors/gate_status.py:66` (and the `:33` docstring), `src/teamctx/connectors/github_checks.py:1` (docstring), `src/teamctx/mcp_server.py:28`, `README.md:24`, `src/teamctx/contract_render.py:27`, `src/teamctx/hook_signal.py:17`
- Test: `tests/test_work_start_cli.py:87`, `tests/test_render_broker_answer.py:139`, plus any asserting the old gate-card copy

- [ ] **Step 1: Find and update the asserting tests first**

```bash
grep -rn "CI is green\|required gate\|a required gate\|all required gates\|failing required" tests src README.md
```

In `tests/test_work_start_cli.py:87`: `assert "CI is green" in result.output` becomes `assert "no failing checks found" in result.output`.
In `tests/test_render_broker_answer.py:139`: `assert "Also checked: CI is green" in text` becomes `assert "Also checked: no failing checks found" in text`.
Update any test asserting `a required gate failed` / `Required gate` to the new copy below.

- [ ] **Step 2: Run tests to verify they fail**

Run: `python -m pytest tests/test_work_start_cli.py tests/test_render_broker_answer.py -v`
Expected: FAIL (production copy still says "CI is green").

- [ ] **Step 3: Apply the copy changes**

`src/teamctx/contract_render.py:27` and `src/teamctx/hook_signal.py:17`:

```python
    "gate": "no failing checks found",
```

`src/teamctx/core/select.py:86` (docstring):

```python
    """The universal a missed-gate card refutes: 'all gates pass for my change'."""
```

`src/teamctx/core/select.py:273-274`:

```python
        why_this_matters=f"a check is failing on files you are changing: {overlap}.",
        reason=f"a check is failing on {overlap}",
```

`src/teamctx/connectors/gate_status.py:66`:

```python
                evidence_summary=f"Check '{gate.gate_name}' is failing on this branch.",
```

`src/teamctx/connectors/gate_status.py:33` (docstring) and `src/teamctx/connectors/github_checks.py:1` (module docstring): replace "required gate(s)" with "check(s)" for internal consistency. Do NOT touch `FAILING_CONCLUSIONS` containing `action_required` (`github_checks.py:24`): that is a GitHub API value, not copy.

`src/teamctx/mcp_server.py:28`: "failing required CI gates" becomes "failing CI checks".

`README.md:24`: "Required checks that are failing on your branch." becomes "Checks that are failing on your branch."

- [ ] **Step 4: Verify and grep for em dashes**

Run: `python -m pytest tests/test_work_start_cli.py tests/test_render_broker_answer.py -v && grep -rnP "\x{2014}" src README.md docs/superpowers/plans/2026-06-29-runtime-honesty-phase2.md || echo "no em dashes"`
Expected: tests PASS; no em dashes.

- [ ] **Step 5: Commit**

```bash
git add -A
git commit -m "refactor(copy): drop unproven 'required'; clear gate reads 'no failing checks found'"
```

---

## Task 8: CLI render buckets for pending and not_applicable

Generalize `cant_verify` and add two lines so every status is surfaced exactly once: a `pending` gate bullet (when it is the cause) plus a `Still running:` line (when a found elsewhere made the kind `heads_up`), and a `Not applicable:` line for out-of-scope docs.

**Files:**
- Modify: `src/teamctx/contract_render.py` (`_HEADLINE`, `_cant_verify_bullets`, new `_still_running_line`, new `_not_applicable_line`, `render_broker_answer` wiring)
- Test: `tests/test_render_broker_answer.py`

- [ ] **Step 1: Write the failing tests**

```python
# tests/test_render_broker_answer.py  (add; build a pending gate and an out-of-scope docs status)
from teamctx.connectors._contract import source_status
from teamctx.contract_render import render_broker_answer
from teamctx.core.broker import broker_answer
from teamctx.core.contracts import RequestContext


def _req() -> RequestContext:
    return RequestContext(
        schema_version="teamctx.request_context.v0", request_id="r", repo="o/n", task="t",
        paths=["a.py"], requested_at="2026-06-29T00:00:00Z",
    )


def _status(family: str, status: str, msg: str):
    return source_status(
        source_id=f"{family}_src", source_family=family, scope={"repo": "o/n"}, status=status,
        observed_at="2026-06-29T00:00:00Z", safe_user_message=msg,
        visibility="warning_when_relevant", policy_reason="metadata only.",
    )


def test_render_pending_gate_is_cant_verify_with_still_running_reason() -> None:
    answer = broker_answer(_req(), signals=(), statuses=(_status("ci_deploy", "pending", "running"),))
    text = render_broker_answer(answer)
    assert "I can't confirm the important things yet" in text
    assert "still running" in text.lower()
    assert "CI is green" not in text


def test_render_not_applicable_docs_gets_its_own_line() -> None:
    answer = broker_answer(_req(), signals=(), statuses=(_status("docs", "not_applicable", "n/a"),))
    text = render_broker_answer(answer)
    assert "Not applicable:" in text
    assert "none of the files in scope are docs you rely on" in text
    # not_applicable docs is non-important: it must not flip the headline to cant_verify.
    assert "I can't confirm the important things yet" not in text
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `python -m pytest tests/test_render_broker_answer.py -k "pending or not_applicable" -v`
Expected: FAIL (no `Still running:` / `Not applicable:` lines; old headline).

- [ ] **Step 3: Write the implementation**

In `src/teamctx/contract_render.py`:

Generalize the headline (`:23`):

```python
    "cant_verify": "Heads up: I can't confirm the important things yet:",
```

Add phrase tables near the existing ones:

```python
_PENDING_PHRASE: dict[CheckId, str] = {
    "gate": "failing checks (CI still running, not confirmed green yet)",
}
_NOT_APPLICABLE_PHRASE: dict[CheckId, str] = {
    "docs": "docs (a docs root is set, but none of the files in scope are docs you rely on)",
}
_PENDING_BULLET = (
    "  • Failing checks: CI checks are still running, so the gate isn't confirmed green yet. "
    "Wait for the build or check the run before relying on a green gate."
)
```

Extend `_cant_verify_bullets` (`:114`) to add the pending bullet without disturbing the existing unreachable bullets:

```python
def _cant_verify_bullets(assessment: WorkStartAssessment) -> list[str]:
    status = {s.check: s.status for s in assessment.checks}
    conflict_unreachable = status.get("conflict") == "unreachable"
    gate_unreachable = status.get("gate") == "unreachable"
    gate_pending = status.get("gate") == "pending"
    fix = (
        "teamctx couldn't reach GitHub. Either it has no access yet (set GITHUB_TOKEN, or "
        "GITHUB_TOKEN_FILE with a path to a token file) or it's a temporary connection issue."
    )
    bullets: list[str] = []
    if conflict_unreachable and gate_unreachable:
        bullets.append(f"  • Open PRs and failing checks: {fix} Until it's back you won't see "
                       "colliding PRs or red CI on your files.")
    elif conflict_unreachable:
        bullets.append(f"  • Open PRs: {fix} Until it's back you won't see colliding PRs on your files.")
    elif gate_unreachable:
        bullets.append(f"  • Failing checks: {fix} Until it's back you won't see red CI on your files.")
    if gate_pending:
        bullets.append(_PENDING_BULLET)
    return bullets
```

Add the two new coverage lines:

```python
def _still_running_line(assessment: WorkStartAssessment) -> str:
    # Surface a pending check unless it is already in the cant_verify bullets (an important
    # pending check is bulleted; here we catch the heads_up case so it is never dropped).
    in_bullets = assessment.kind == "cant_verify"
    gaps = [
        _PENDING_PHRASE[s.check]
        for s in assessment.checks
        if s.status == "pending" and not (in_bullets and s.check in IMPORTANT_CHECKS)
    ]
    if not gaps:
        return ""
    return "  Still running: " + "; ".join(gaps) + "."


def _not_applicable_line(assessment: WorkStartAssessment) -> str:
    gaps = [
        _NOT_APPLICABLE_PHRASE[s.check] for s in assessment.checks if s.status == "not_applicable"
    ]
    if not gaps:
        return ""
    return "  Not applicable: " + "; ".join(gaps) + "."
```

Wire them into `render_broker_answer` (after the `not_checked` block, `:75-77`):

```python
    not_checked = _not_checked_line(assessment)
    if not_checked:
        lines.append(not_checked)
    still_running = _still_running_line(assessment)
    if still_running:
        lines.append(still_running)
    not_applicable = _not_applicable_line(assessment)
    if not_applicable:
        lines.append(not_applicable)
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `python -m pytest tests/test_render_broker_answer.py -v`
Expected: PASS (including the pre-existing render tests; existing unreachable bullets are unchanged).

- [ ] **Step 5: Commit**

```bash
git add src/teamctx/contract_render.py tests/test_render_broker_answer.py
git commit -m "feat(render): cant_verify covers pending; add Still running and Not applicable lines"
```

---

## Task 9: Hook signal distinguishes a pending gate from an unreachable source

The glanceable hook must say something true for a pending gate ("CI checks are still running, so it can't confirm the gate is green yet") instead of "couldn't reach GitHub". `not_applicable` docs stays unheadlined in the hook, exactly as `not_configured` is today.

**Files:**
- Modify: `src/teamctx/hook_signal.py` (`hook_signal` passes the assessment to `_cant_verify`; `_cant_verify` branches on pending vs unreachable; new imports)
- Test: `tests/test_hook_signal.py`

- [ ] **Step 1: Write the failing test**

```python
# tests/test_hook_signal.py  (add)
from teamctx.connectors._contract import source_status
from teamctx.core.broker import broker_answer
from teamctx.core.contracts import RequestContext
from teamctx.hook_signal import hook_signal


def _req() -> RequestContext:
    return RequestContext(
        schema_version="teamctx.request_context.v0", request_id="r", repo="o/n", task="t",
        paths=["a.py"], requested_at="2026-06-29T00:00:00Z",
    )


def test_hook_pending_gate_says_checks_running_not_unreachable() -> None:
    pending = source_status(
        source_id="github_check_runs", source_family="ci_deploy", scope={"repo": "o/n"},
        status="pending", observed_at="2026-06-29T00:00:00Z",
        safe_user_message="running", visibility="warning_when_relevant", policy_reason="m.",
    )
    answer = broker_answer(_req(), signals=(), statuses=(pending,))
    out = hook_signal(answer, file_path="a.py", token_present=True)
    assert "still running" in out.lower()
    assert "couldn't reach GitHub" not in out
```

- [ ] **Step 2: Run test to verify it fails**

Run: `python -m pytest tests/test_hook_signal.py::test_hook_pending_gate_says_checks_running_not_unreachable -v`
Expected: FAIL (the current `_cant_verify` returns the unreachable copy regardless of cause).

- [ ] **Step 3: Write the implementation**

In `src/teamctx/hook_signal.py`, extend the imports:

```python
from teamctx.assessment import IMPORTANT_CHECKS, CheckState, WorkStartAssessment, assess
```

Pass the assessment into `_cant_verify` (`:29-30`):

```python
    if a.kind == "cant_verify":
        return _cant_verify(a, token_present)
```

Rewrite `_cant_verify` to branch on the cause (`:44-57`):

```python
def _cant_verify(a: WorkStartAssessment, token_present: bool) -> str:
    important_unreachable = any(
        s.status == "unreachable" and s.check in IMPORTANT_CHECKS for s in a.checks
    )
    if important_unreachable:
        if not token_present:
            return (
                "teamctx couldn't check what else is happening around this file. It doesn't have "
                "access to GitHub yet. To switch that on, set GITHUB_TOKEN in your environment "
                "(or GITHUB_TOKEN_FILE with a path to a token file). If you'd rather not connect "
                "it right now, keep working; you just won't get a heads-up about open pull requests "
                "on the same files or checks that are failing."
            )
        return (
            "teamctx couldn't reach GitHub just now, so it couldn't check for open pull requests or "
            "failing checks on these files. This is likely a transient connection issue. You won't "
            "get those warnings this session, so glance at GitHub yourself if this file is sensitive."
        )
    # the remaining cause of cant_verify is a pending gate.
    return (
        "teamctx: CI checks on this branch are still running, so it can't confirm the gate is "
        "green yet. If a green build matters for this edit, wait for it or check the run yourself."
    )
```

- [ ] **Step 4: Run test to verify it passes**

Run: `python -m pytest tests/test_hook_signal.py -v`
Expected: PASS (existing unreachable / no-token hook tests still pass; they exercise the `important_unreachable` branch).

- [ ] **Step 5: Commit**

```bash
git add src/teamctx/hook_signal.py tests/test_hook_signal.py
git commit -m "feat(hook): pending gate gets a 'checks still running' signal, not 'couldn't reach'"
```

---

## Task 10: Record the additive-within-v0 protocol note

The two enum extensions widen the published v0 vocabulary without removing or changing any existing value, so existing documents stay valid. Record it.

**Files:**
- Modify: `CHANGELOG.md`

- [ ] **Step 1: Read the changelog head to match its format**

Run: `sed -n '1,30p' CHANGELOG.md`

- [ ] **Step 2: Add the entry**

Following the file's existing heading style, add an entry recording: `SourceStatusValue` gains `pending` and `not_applicable`; `Completeness` gains `incomplete[pending]` and `not_applicable[out-of-scope]`. State that this is additive within `v0` (no existing value changed or removed; existing contract documents remain valid), and name the closed gap (a gate mid-build no longer reads green; a docs root scanned with nothing relied-on in scope no longer reads current). No em dashes.

- [ ] **Step 3: Commit**

```bash
git add CHANGELOG.md
git commit -m "docs(changelog): additive v0 note for pending/not_applicable coverage states"
```

---

## Task 11: Full-suite gate and integration sweep

- [ ] **Step 1: Run the whole gate**

Run: `python -m pytest -q -p no:cacheprovider && ruff check src tests && python -m mypy src`
Expected: all green (target: 332 prior + the new tests). If mypy flags `Literal` narrowing in `_status_for` or `assess_completeness`, the new branches should already satisfy it; do not add `# type: ignore` without understanding the cause.

- [ ] **Step 2: Em-dash ship gate**

Run: `grep -rnP "\x{2014}" src tests README.md CHANGELOG.md docs/superpowers/plans/2026-06-29-runtime-honesty-phase2.md || echo "clean"`
Expected: `clean`.

- [ ] **Step 3: codex adversarial diff-review (before merge)**

Diff the branch against `main` and hand the diff plus this plan and the spec sections 1.4 to 1.7 to codex (`codex exec --dangerously-bypass-approvals-and-sandbox`, backgrounded, ANSI-stripped on read). Verify each finding against the code as CTO-arbiter before acting. Phase 1's review caught three real split-brain P1s a self-pass missed, so this is not optional.

- [ ] **Step 4: Merge when green and reviewed**

Per the finish-branch rule (merge + push, no PR): merge `feat/runtime-honesty-phase2` to `main` locally and push. Then update `docs/product/plan/CURRENT.md` to mark Phase 2 done.

---

## Self-review (against spec 1.4 to 1.7)

- **1.4 gate honesty:** "required" swept from select.py/gate_status.py/mcp_server.py/README (Task 7); "CI is green" becomes "no failing checks found" (Task 7); in-progress runs surface `pending`, found-over-pending (Task 4); pending render (Task 8) and hook (Task 9). Covered.
- **1.5 docs honesty:** init stops auto-enabling docs_root (Task 6); `not_applicable` when scanned-but-out-of-scope via the `docs.py` -> `normalize_superseded_docs` signature change (Task 5). Covered.
- **1.6 assessment model:** `CheckStatus` gains both states; `_status_for` maps both; pinned kind precedence (Task 3); render buckets cant_verify-generalized + Not applicable line + hook pending branch (Tasks 8, 9). Covered.
- **1.7 carrier:** `SourceStatusValue` (Task 1) and `Completeness` (Task 2) extensions; `assess_completeness` precedence (Task 2); valuation propagation needs no change (locked by a test in Task 3); connector emission (Tasks 4, 5); additive-within-v0 changelog note (Task 10). Covered.
- **Type consistency:** `pending` / `not_applicable` are the `CheckStatus` and `SourceStatusValue` spellings; `incomplete[pending]` / `not_applicable[out-of-scope]` are the `Completeness` spellings; `_status_for` maps the latter to the former. Consistent across Tasks 1 to 9.
- **Out of scope (Phase 3, not here):** the onboard command, the CLAUDE.md snippet honesty/migration (cli.py:543), the gitignore negation, `verify_health`. Not touched by any task above.
