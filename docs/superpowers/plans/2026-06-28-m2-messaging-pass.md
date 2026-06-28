# M2 — Messaging Pass Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Replace the shared work-start render's jargon/raw-reason-code output with signal-led plain prose, driven by one shared `assess()` classification that both the hook and the render consume.

**Architecture:** A new pure `assessment.py` maps a `BrokerAnswer` to a `WorkStartAssessment` (kind + per-check status + findings). `hook_signal` refactors onto it (output unchanged). `contract_render.render_broker_answer` is rewritten to render signal-led prose from the assessment; the old `render_selection` is removed. All `render_broker_answer` consumers (work-start CLI+MCP, the probe commands, the eval pack) inherit the new prose, so ~30 assertions across 9 test files get updated.

**Tech Stack:** Python 3.12, mypy `--strict`, ruff (`E,F,I,N,W,UP,B,SIM`, line 100), pytest.

Spec: `docs/superpowers/specs/2026-06-28-m2-messaging-pass-design.md`.

---

## File structure

- **Create** `src/teamctx/assessment.py` — `assess(answer) -> WorkStartAssessment` (+ `CheckState`). Pure.
- **Modify** `src/teamctx/hook_signal.py` — refactor onto `assess`; identical output.
- **Modify** `src/teamctx/contract_render.py` — `render_broker_answer` renders prose via `assess`; remove `render_selection`; keep `_authority_line`/`render_contract_context` and the other helpers.
- **Create** `tests/test_assessment.py`. **Rewrite** `tests/test_render_selection.py` → `tests/test_render_broker_answer.py`.
- **Update** assertions in: `test_work_start_cli`, `test_mcp_server`, `test_broker`, `test_contract_terminal`, `test_eval`, `test_gate_probe_cli`, `test_docs_probe_cli`, `test_issue_probe_cli`, `test_work_start_answer`.

Order: Task 1 (assessment) → 2 (hook refactor) → 3 (render) → 4 (render tests) → 5 (ripple) → 6 (verify). 2 and 4/5 depend on 1/3.

---

## Task 1: The shared classification (`assessment.py`)

**Files:** Create `src/teamctx/assessment.py`; Test `tests/test_assessment.py`.

- [ ] **Step 1: Write the failing tests** — `tests/test_assessment.py`. Reuse the broker-driven construction from `test_hook_signal.py` (copy its `_request`, `_collision_signal`, `_fresh_status`, `_unavailable_status` helpers verbatim — they build real `BrokerAnswer`s via `broker_answer`):

```python
from __future__ import annotations

from teamctx.assessment import assess
from teamctx.connectors._contract import metadata_only_policy, source_status
from teamctx.core.broker import broker_answer
from teamctx.core.contracts import RequestContext, SourceSignal, SourceStatus


def _request(paths=("src/app.py",)) -> RequestContext:
    return RequestContext(
        schema_version="teamctx.request_context.v0", request_id="t", repo="acme/widgets",
        branch="feature", task="work", paths=list(paths), linked_issues=[],
        requested_at="2026-06-28T00:00:00Z", requesting_principal=None,
    )


def _collision_signal() -> SourceSignal:
    return SourceSignal(
        schema_version="teamctx.source_signal.v0", id="sig_pr_7", signal_type="collision",
        source_family="git_hosting", scope={"repo": "acme/widgets", "files": ["src/app.py"]},
        evidence_summary="PR #7 changes src/app.py", source_display="github acme/widgets#7",
        freshness="fresh", confidence="high", visibility="visible",
        created_at="2026-06-28T00:00:00Z", observed_at="2026-06-28T00:00:00Z",
        expires_at="next_refresh", policy=metadata_only_policy("pr metadata is evidence"),
    )


def _fresh_status(family: str) -> SourceStatus:
    return source_status(
        source_id=f"{family}-probe", source_family=family, scope={"repo": "acme/widgets"},
        status="fresh", observed_at="2026-06-28T00:00:00Z", safe_user_message="checked",
        visibility="silent", policy_reason="status only",
    )


def _unavailable_status(family: str) -> SourceStatus:
    return source_status(
        source_id=f"{family}-probe", source_family=family, scope={"repo": "acme/widgets"},
        status="unavailable", observed_at="2026-06-28T00:00:00Z", safe_user_message="no access",
        visibility="silent", policy_reason="status only",
    )


def test_found_is_heads_up_and_card_grouped_to_conflict() -> None:
    a = assess(broker_answer(_request(), [_collision_signal()], [_fresh_status("git_hosting")]))
    assert a.kind == "heads_up"
    conflict = next(c for c in a.checks if c.check == "conflict")
    assert conflict.status == "found"
    assert len(conflict.cards) == 1
    assert len(a.findings) == 1


def test_unreachable_important_is_cant_verify() -> None:
    a = assess(broker_answer(_request(), [], [_unavailable_status("git_hosting")]))
    assert a.kind == "cant_verify"
    assert next(c for c in a.checks if c.check == "conflict").status == "unreachable"


def test_clear_important_with_only_policy_gaps_is_ready() -> None:
    a = assess(broker_answer(_request(), [], [_fresh_status("git_hosting")]))
    assert a.kind == "ready"
    assert next(c for c in a.checks if c.check == "conflict").status == "clear"
    # criteria/docs not configured -> not_configured, never headlined
    assert next(c for c in a.checks if c.check == "criteria").status == "not_configured"


def test_checks_are_ordered_conflict_criteria_docs_gate() -> None:
    a = assess(broker_answer(_request(), [], [_fresh_status("git_hosting")]))
    assert [c.check for c in a.checks] == ["conflict", "criteria", "docs", "gate"]
```

> First confirm the helper imports exist (they do in `test_hook_signal.py`): `grep -nE "def source_status|def metadata_only_policy" src/teamctx/connectors/_contract.py`. If a signature differs, copy `test_hook_signal.py`'s exact helpers.

- [ ] **Step 2: Run to verify failure** — `pytest tests/test_assessment.py -v` → FAIL (no module `teamctx.assessment`).

- [ ] **Step 3: Implement** — `src/teamctx/assessment.py`:

```python
"""Classify the broker's answer into one work-start assessment: kind + per-check status.

One shared classification consumed by both the hook (a glanceable line) and the CLI/MCP render
(a fuller report) — so there is a single voice and the important-vs-low-stakes split lives in one
place. Pure: no I/O.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Literal

from teamctx.core.broker import BrokerAnswer
from teamctx.core.contracts import ContextCard
from teamctx.core.evaluate import Valuation

CheckId = Literal["conflict", "criteria", "docs", "gate"]
CheckStatus = Literal["clear", "found", "unreachable", "not_configured"]

# CARD_KINDS verdict labels -> our check ids, in the order we present them.
_LABELS: tuple[tuple[str, CheckId], ...] = (
    ("Conflict check", "conflict"),
    ("Criteria check", "criteria"),
    ("Docs check", "docs"),
    ("Gate check", "gate"),
)
# card.reason_code prefix -> check id (codes: collision.*, criteria.*, doc.*, gate.*)
_REASON_PREFIX: dict[str, CheckId] = {
    "collision": "conflict", "criteria": "criteria", "doc": "docs", "gate": "gate",
}
_IMPORTANT: frozenset[CheckId] = frozenset({"conflict", "gate"})


@dataclass(frozen=True)
class CheckState:
    check: CheckId
    status: CheckStatus
    cards: tuple[ContextCard, ...]


@dataclass(frozen=True)
class WorkStartAssessment:
    kind: Literal["ready", "heads_up", "cant_verify"]
    checks: tuple[CheckState, ...]          # ordered conflict, criteria, docs, gate
    findings: tuple[ContextCard, ...]       # all finding cards in selection order (for the hook)


def _status_for(valuation: Valuation) -> CheckStatus:
    if valuation.value == "true":
        return "clear"
    if valuation.value == "false":
        return "found"
    if valuation.reason == "incomplete[stale-dep]":
        return "unreachable"
    return "not_configured"


def _check_of_card(card: ContextCard) -> CheckId | None:
    return _REASON_PREFIX.get(card.reason_code.split(".", 1)[0])


def assess(answer: BrokerAnswer) -> WorkStartAssessment:
    verdicts: dict[str, Valuation] = {label: val for label, val in answer.verdicts}
    cards_by_check: dict[CheckId, list[ContextCard]] = {
        "conflict": [], "criteria": [], "docs": [], "gate": []
    }
    findings: list[ContextCard] = []
    for card in answer.selection.cards:
        check = _check_of_card(card)
        if check is not None:
            cards_by_check[check].append(card)
            findings.append(card)

    states: list[CheckState] = []
    for label, check in _LABELS:
        valuation = verdicts.get(label)
        status: CheckStatus = _status_for(valuation) if valuation is not None else "not_configured"
        states.append(CheckState(check=check, status=status, cards=tuple(cards_by_check[check])))

    kind: Literal["ready", "heads_up", "cant_verify"]
    if any(s.status == "found" for s in states):
        kind = "heads_up"
    elif any(s.status == "unreachable" and s.check in _IMPORTANT for s in states):
        kind = "cant_verify"
    else:
        kind = "ready"
    return WorkStartAssessment(kind=kind, checks=tuple(states), findings=tuple(findings))
```

- [ ] **Step 4: Run** — `pytest tests/test_assessment.py -v` → PASS. `ruff check src/teamctx/assessment.py tests/test_assessment.py`, `mypy src/teamctx/assessment.py` → clean.

- [ ] **Step 5: Commit**

```bash
git add src/teamctx/assessment.py tests/test_assessment.py
git commit -m "feat: assessment — one shared work-start classification (kind + per-check status)"
```

---

## Task 2: Refactor `hook_signal` onto `assess`

**Files:** Modify `src/teamctx/hook_signal.py`; Test `tests/test_hook_signal.py` (should stay green).

- [ ] **Step 1: Replace `hook_signal`'s derivation with `assess`.** The output strings stay identical; only the internal source of truth moves. Replace the body of `hook_signal` and the `_ready`/`_heads_up` signatures so they read the assessment. Keep `_cant_verify`, `_join`, and the `_CLEAR_PHRASE` *values* (re-keyed to `CheckId`). New `src/teamctx/hook_signal.py`:

```python
"""Map the broker's answer to one glanceable hook signal: ready / heads up / can't verify.

The hook injects a short signal before an edit — not the full CLI report. Per the surfaced-text
principle, it speaks to a human about to decide: a clean *ready* that names what it checked, a
*heads up* with the specific item, or *can't verify* when a source that matters was unreachable.
Low-stakes coverage gaps (a check not configured) are never headlined.
"""

from __future__ import annotations

from teamctx.assessment import CheckState, WorkStartAssessment, assess
from teamctx.core.broker import BrokerAnswer
from teamctx.core.contracts import ContextCard

_CLEAR_PHRASE = {
    "conflict": "no open pull requests touch these files",
    "gate": "CI is green",
    "docs": "the docs you rely on are current",
    "criteria": "the linked issue's criteria are unchanged",
}


def hook_signal(answer: BrokerAnswer, *, file_path: str, token_present: bool) -> str:
    """One glanceable signal for the PreToolUse injection. Empty string = nothing worth saying."""

    a = assess(answer)
    if a.kind == "heads_up":
        return _heads_up(a.findings, file_path)
    if a.kind == "cant_verify":
        return _cant_verify(token_present)
    return _ready(a.checks, file_path)


def _heads_up(findings: tuple[ContextCard, ...], file_path: str) -> str:
    lines = [f"teamctx — before you edit {file_path}, from the team's current work:"]
    lines.extend(f"  • {card.text} — {card.why_this_matters}" for card in findings)
    lines.append(
        "Factor these into your plan, and surface anything relevant to your human "
        "collaborator so they can decide."
    )
    return "\n".join(lines)


def _cant_verify(token_present: bool) -> str:
    if not token_present:
        return (
            "teamctx couldn't check what else is happening around this file — it doesn't have "
            "access to GitHub yet. To switch that on, run `teamctx install-hook` and it'll "
            "walk you through giving it a token. If you'd rather not connect it right now, keep "
            "working — you just won't get a heads-up about open pull requests on the same files "
            "or checks that are failing."
        )
    return (
        "teamctx couldn't reach GitHub just now, so it couldn't check for open pull requests or "
        "failing checks on these files — likely a transient connection issue. You won't get those "
        "warnings this session, so glance at GitHub yourself if this file is sensitive."
    )


def _ready(checks: tuple[CheckState, ...], file_path: str) -> str:
    clear = [_CLEAR_PHRASE[s.check] for s in checks if s.status == "clear"]
    if not clear:
        return ""
    return f"teamctx — looks clear to start on {file_path}: {_join(clear)}."


def _join(items: list[str]) -> str:
    if len(items) == 1:
        return items[0]
    return ", ".join(items[:-1]) + ", and " + items[-1]
```

Note: `_ready` now iterates `checks` (conflict, criteria, docs, gate order) — same clear-phrase set, same order, so the output string is identical to before. `_heads_up` iterates `findings` (selection order) — identical to the old section-filtered list.

- [ ] **Step 2: Run** — `pytest tests/test_hook_signal.py tests/test_hook.py -v` → all PASS unchanged (the hook's behavior is identical). `ruff check src/teamctx/hook_signal.py`, `mypy src/teamctx/hook_signal.py` → clean.

- [ ] **Step 3: Commit**

```bash
git add src/teamctx/hook_signal.py
git commit -m "refactor: hook_signal derives from shared assess() (output unchanged)"
```

---

## Task 3: The prose render (`contract_render.py`)

**Files:** Modify `src/teamctx/contract_render.py`.

- [ ] **Step 1: Implement the prose render.** Add `from teamctx.assessment import CheckState, WorkStartAssessment, assess` and `from teamctx.core.select import ContextSelection` (already imported). **Replace** the existing `render_selection` and `render_broker_answer` functions and the `_verdict_line` function with the prose render below. Keep `_authority_line`, `render_contract_context`, `render_contract_why`, `render_contract_open_source`, and all the `*_label` helpers untouched.

```python
_HEADLINE = {
    "ready": "Looks clear to start.",
    "heads_up": "Before you start — worth handling first:",
    "cant_verify": "Heads up — I couldn't check the important things:",
}
_CLEAR_PHRASE = {
    "conflict": "no open PRs touch your files",
    "gate": "CI is green",
    "docs": "the docs you rely on are current",
    "criteria": "the linked issue's criteria are unchanged",
}
_NOT_CHECKED_PHRASE = {
    "criteria": "spec changes — no issue is linked to this branch (link one to enable)",
    "docs": "docs — no docs root is configured (set work_start.docs_root to enable)",
    "gate": "failing checks — couldn't determine your branch",
    "conflict": "open PRs — couldn't determine the repository",
}
_FINDING_ACTION = {
    "conflict": "look at it before you edit so you don't undo each other's work",
    "criteria": "re-check the criteria before you rely on them",
    "docs": "rely on the current one instead",
    "gate": "fix it or wait for a green build before relying on it",
}


def render_broker_answer(answer: BrokerAnswer) -> str:
    """The one render every transport uses: a signal-led plain-prose report of the broker's
    answer. Decision-enabling; gaps carry their reason and how to turn them on. Deterministic,
    never via an LLM, and prints — it never blocks."""

    from teamctx.assessment import assess  # local import keeps the core import DAG acyclic

    a = assess(answer)
    lines = [_HEADLINE[a.kind]]
    lines.extend(_finding_bullets(a))
    coverage = _coverage_line(a)
    if coverage:
        lines.append(coverage)
    not_checked = _not_checked_line(a)
    if not_checked:
        lines.append(not_checked)
    lines.extend(_authority_block(answer.selection))
    return "\n".join(lines) + "\n"


def _finding_bullets(a: WorkStartAssessment) -> list[str]:
    if a.kind == "heads_up":
        return [f"  • {_finding_text(card)}" for card in a.findings]
    if a.kind == "cant_verify":
        return _cant_verify_bullets(a)
    return []


def _finding_text(card: ContextCard) -> str:
    from teamctx.assessment import _check_of_card

    check = _check_of_card(card)
    action = _FINDING_ACTION.get(check, "") if check is not None else ""
    pr = _gh_hint(card.source_display)
    base = f"{card.text} — {action}" if action else card.text
    return f"{base}{pr}"


def _gh_hint(source_display: str) -> str:
    marker = source_display.rfind("#")
    if marker == -1:
        return ""
    digits = ""
    for ch in source_display[marker + 1:]:
        if ch.isdigit():
            digits += ch
        else:
            break
    return f" (gh pr view {digits})" if digits else ""


def _cant_verify_bullets(a: WorkStartAssessment) -> list[str]:
    status = {s.check: s.status for s in a.checks}
    conflict = status.get("conflict") == "unreachable"
    gate = status.get("gate") == "unreachable"
    fix = (
        "teamctx couldn't reach GitHub — either it has no access yet (run `teamctx install-hook` "
        "to connect it) or it's a temporary connection issue."
    )
    if conflict and gate:
        return [f"  • Open PRs and failing checks: {fix} Until it's back you won't see colliding "
                "PRs or red CI on your files."]
    if conflict:
        return [f"  • Open PRs: {fix} Until it's back you won't see colliding PRs on your files."]
    if gate:
        return [f"  • Failing checks: {fix} Until it's back you won't see red CI on your files."]
    return []


def _coverage_line(a: WorkStartAssessment) -> str:
    clear = [_CLEAR_PHRASE[s.check] for s in a.checks if s.status == "clear"]
    if not clear:
        return ""
    label = "Checked: " if a.kind == "ready" else "Also checked: "
    return "  " + label + "; ".join(clear) + "."


def _not_checked_line(a: WorkStartAssessment) -> str:
    gaps = [_NOT_CHECKED_PHRASE[s.check] for s in a.checks if s.status == "not_configured"]
    if not gaps:
        return ""
    return "  Not checked: " + "; ".join(gaps) + "."


def _authority_block(selection: ContextSelection) -> list[str]:
    if not selection.authority:
        return []
    lines = ["", "Authority"]
    lines.extend(_authority_line(entry) for entry in selection.authority)
    return lines
```

(Delete `render_selection` and `_verdict_line` entirely. If `from teamctx.core.evaluate import Valuation` becomes unused after removing `_verdict_line`, drop that import to satisfy ruff F401.)

- [ ] **Step 2: Run** — `pytest tests/test_render_selection.py -v` will now FAIL (it calls the removed `render_selection`); that's expected — Task 4 rewrites it. Confirm `ruff check src/teamctx/contract_render.py` and `mypy src/teamctx/contract_render.py` are clean.

- [ ] **Step 3: Commit**

```bash
git add src/teamctx/contract_render.py
git commit -m "feat: signal-led prose render for work-start (plain, decision-enabling, gaps carry fix)"
```

---

## Task 4: Rewrite the render tests

**Files:** Delete `tests/test_render_selection.py`; Create `tests/test_render_broker_answer.py`.

- [ ] **Step 1: Replace the test file.** `git rm tests/test_render_selection.py`, then create `tests/test_render_broker_answer.py` (build real `BrokerAnswer`s via `broker_answer`, assert the new prose, and assert the old jargon is gone):

```python
from __future__ import annotations

from teamctx.connectors._contract import metadata_only_policy, source_status
from teamctx.contract_render import render_broker_answer
from teamctx.core.authority import AuthorityDecl
from teamctx.core.broker import broker_answer
from teamctx.core.contracts import RequestContext, SourceSignal, SourceStatus


def _request(paths=("src/app.py",), issues=()) -> RequestContext:
    return RequestContext(
        schema_version="teamctx.request_context.v0", request_id="t", repo="acme/widgets",
        branch="feature", task="work", paths=list(paths), linked_issues=list(issues),
        requested_at="2026-06-28T00:00:00Z", requesting_principal=None,
    )


def _collision_signal() -> SourceSignal:
    return SourceSignal(
        schema_version="teamctx.source_signal.v0", id="sig_pr_7", signal_type="collision",
        source_family="git_hosting", scope={"repo": "acme/widgets", "files": ["src/app.py"]},
        evidence_summary="PR #7 changes src/app.py", source_display="github acme/widgets#7",
        freshness="fresh", confidence="high", visibility="visible",
        created_at="2026-06-28T00:00:00Z", observed_at="2026-06-28T00:00:00Z",
        expires_at="next_refresh", policy=metadata_only_policy("pr metadata is evidence"),
    )


def _fresh(family: str) -> SourceStatus:
    return source_status(
        source_id=f"{family}-probe", source_family=family, scope={"repo": "acme/widgets"},
        status="fresh", observed_at="2026-06-28T00:00:00Z", safe_user_message="checked",
        visibility="silent", policy_reason="status only",
    )


def _unavailable(family: str) -> SourceStatus:
    return source_status(
        source_id=f"{family}-probe", source_family=family, scope={"repo": "acme/widgets"},
        status="unavailable", observed_at="2026-06-28T00:00:00Z", safe_user_message="no access",
        visibility="silent", policy_reason="status only",
    )


def _no_jargon(text: str) -> None:
    for bad in ("UNKNOWN", "NOT CLEAR", "incomplete[", "git_hosting", "ci_deploy",
                "coverage incomplete", "absence is not an all-clear"):
        assert bad not in text, f"jargon leaked: {bad!r}"


def test_ready_headline_names_clear_checks_and_lists_gaps() -> None:
    text = render_broker_answer(broker_answer(_request(), [], [_fresh("git_hosting")]))
    assert text.startswith("Looks clear to start.")
    assert "no open PRs touch your files" in text
    assert "Not checked:" in text and "no issue is linked to this branch" in text
    _no_jargon(text)


def test_heads_up_surfaces_the_pr_with_action() -> None:
    text = render_broker_answer(
        broker_answer(_request(), [_collision_signal()], [_fresh("git_hosting")])
    )
    assert text.startswith("Before you start — worth handling first:")
    assert "PR #7" in text
    assert "gh pr view 7" in text
    _no_jargon(text)


def test_cant_verify_when_github_unreachable() -> None:
    text = render_broker_answer(broker_answer(_request(), [], [_unavailable("git_hosting")]))
    assert text.startswith("Heads up — I couldn't check the important things:")
    assert "couldn't reach GitHub" in text
    assert "teamctx install-hook" in text
    _no_jargon(text)


def test_authority_section_surfaces_a_conflict() -> None:
    decls = [
        AuthorityDecl(subject="rounding-cap", source="ticket", priority=10, value="5", fresh=True),
        AuthorityDecl(subject="rounding-cap", source="policy", priority=10, value="3", fresh=True),
    ]
    text = render_broker_answer(broker_answer(_request(), [], [_fresh("git_hosting")], decls))
    assert "Authority" in text
    assert "rounding-cap" in text
    assert "CONFLICTED" in text


def test_no_authority_section_without_declarations() -> None:
    text = render_broker_answer(broker_answer(_request(), [], [_fresh("git_hosting")]))
    assert "Authority" not in text
```

- [ ] **Step 2: Run** — `pytest tests/test_render_broker_answer.py -v` → PASS. `ruff check tests/test_render_broker_answer.py`, `mypy` (if tests are checked) clean.

- [ ] **Step 3: Commit**

```bash
git add tests/test_render_broker_answer.py
git rm --cached tests/test_render_selection.py 2>/dev/null || true
git commit -m "test: render_broker_answer prose tests; remove render_selection tests"
```

---

## Task 5: Update the rippled assertions (the consumers)

The render output changed, so every test that asserts the old work-start render strings now fails. Update each to the new prose. **Method:** run `pytest -q`, open each failing test, and replace the old-string assertion with the new prose the render now emits (use the mapping below; run the specific test with `-v` and read the actual output to confirm the exact string).

**Old → new mapping** (the render no longer emits the left column):
- `"Working context"` → gone; the report starts with a headline (`Looks clear to start.` / `Before you start — worth handling first:` / `Heads up — I couldn't check the important things:`). Assert a headline or a specific line instead.
- `"Conflict check: clear"` / `"Gate check: clear"` → `"no open PRs touch your files"` / `"CI is green"` (in the `Checked:` line).
- `"Criteria check: clear"` / `"Docs check: clear"` → `"the linked issue's criteria are unchanged"` / `"the docs you rely on are current"`.
- `"Conflict check: NOT CLEAR"` (+ `"PR #7"`) → the heads-up headline + `"PR #7"` (still present) + `"gh pr view 7"`.
- `"Conflict check: UNKNOWN"` / `"UNKNOWN — coverage incomplete (incomplete[...])"` → for the no-token case, `"couldn't reach GitHub"` + `"teamctx install-hook"`; for a not-configured check, the `"Not checked: …"` line.
- `"Coverage"` / `"not an all-clear"` / `"absence is not an all-clear"` → gone; honesty now lives in the `Checked:` / `Not checked:` / can't-verify lines.

**Per-file checklist** (run `pytest <file> -v` to see the exact failing assertions):
- [ ] `tests/test_work_start_cli.py` (9): the no-token test asserts `"Working context"`, `"Coverage"`, `"not an all-clear"`, `"Conflict check: UNKNOWN"` → assert the no-token render now: `"couldn't reach GitHub"` + `"teamctx install-hook"`, exit 0. The all-four-clear test asserts the four `"X check: clear"` → assert the new clear phrases (`"no open PRs touch your files"`, `"CI is green"`, etc.).
- [ ] `tests/test_mcp_server.py` (6): replace `"Working context"` / `"Conflict check: UNKNOWN"` with the can't-verify prose; the collision test's `"Conflict check: NOT CLEAR"` → the heads-up headline; keep `"PR #7"`.
- [ ] `tests/test_work_start_answer.py` (3): `test_render_work_start_still_renders` asserts `"Working context"` + `"Conflict check:"` → assert a new prose line (e.g. `"couldn't reach GitHub"` or a clear phrase, per the stubbed scenario).
- [ ] `tests/test_broker.py` (6): these assert render strings via `render_broker_answer`/the old verdict lines → update to the new prose for each scenario.
- [ ] `tests/test_contract_terminal.py` (4): if it asserts work-start render strings, update; if it tests the legacy `render_contract_context` (unchanged), leave it.
- [ ] `tests/test_eval.py` (4): the eval context arm is now the new prose → update the asserted substrings to the new phrasing (the eval's behavior is unchanged; only the carried text changed).
- [ ] `tests/test_gate_probe_cli.py` (2), `tests/test_docs_probe_cli.py` (1), `tests/test_issue_probe_cli.py` (4): these probes render via `_work_start_view` → `render_broker_answer`; update their asserted strings to the new prose (e.g. the docs-probe "superseded" assertion still finds the doc card text in the heads-up bullet; the gate/issue ones move to the new clear/heads-up/can't-verify phrasing).

- [ ] **Commit** after the suite is green:

```bash
git add tests/
git commit -m "test: update render-string assertions to the new prose across all consumers"
```

---

## Task 6: Full verification

- [ ] **Step 1:** `pytest -q` → all pass.
- [ ] **Step 2:** `ruff check src tests` → clean.
- [ ] **Step 3:** `mypy src` → clean.
- [ ] **Step 4:** Spot-check the real output: `printf '%s' '{"hook_event_name":"x"}' ` is not needed — instead, eyeball `python -c "from teamctx.work_start import render_work_start"` imports cleanly, and the render tests cover the three signals. Commit any fixups:

```bash
git add -A && git commit -m "chore: lint/type fixups for M2" || echo "nothing to fix"
```

---

## Self-Review

**Spec coverage:** assessment.py (Component 1) → Task 1. hook_signal refactor (Component 2) → Task 2. prose render + per-(check,status) copy + coverage lines + authority (Component 3) → Task 3, tested in Task 4. The ripple (work-start CLI+MCP, probes, eval) → Task 5. Non-goals (json, card-copy, legacy) correctly untouched. The "verify render_selection usage" item is resolved: it's only called by `render_broker_answer`, so Task 3 removes it and Task 4 replaces its tests.

**Placeholder scan:** Tasks 1–4 have complete code. Task 5 is assertion-updating to a fully-determined new output (the render in Task 3) — the mapping + per-file list make each change concrete; the implementer reads the actual new output to pin exact strings (the honest way to do a render-copy ripple).

**Type/name consistency:** `assess`, `WorkStartAssessment`, `CheckState`, `CheckId`/`CheckStatus`, `_check_of_card`, `findings`, `_CLEAR_PHRASE` (re-keyed to `CheckId`) are consistent across assessment.py, hook_signal.py, and contract_render.py. Verdict labels ("Conflict check"/"Criteria check"/"Docs check"/"Gate check") match `CARD_KINDS`. `card.reason_code` prefixes (collision/criteria/doc/gate) match `core/select.py`.
