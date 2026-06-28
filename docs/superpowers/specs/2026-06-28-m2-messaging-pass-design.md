# M2: the messaging pass (Sprint 2, Slice A-follow)

**Status:** design, awaiting CPO review · **Date:** 2026-06-28 · Governs:
[surfaced-text principle](../../product/vision/reality-grounding-strategy-2026-06.md)

## Purpose

Bring the **shared** work-start render up to the surfaced-text principle, done once so every
transport inherits it: plain prose (no jargon, no raw reason codes), decision-enabling, gaps get
reason + fix + fallback, honest coverage shown plainly. Lead with the same *ready / heads-up /
can't-verify* signal M1's hook proved, and **share the classification** between the hook and the
render so there is one voice and the M1 carry-forward (a *stale* Docs/Criteria source) is handled
in one place.

## Scope / ripple (read this: it's broad by design)

`render_broker_answer` is the single render for the work-start answer. Reworking it changes the
output of **everything that calls it**: `work-start` (CLI + MCP), the `gate-probe` / `docs-probe` /
`issue-probe` commands (via `cli._work_start_view`), and the **eval pack** context arm
(`eval/prompts.py`). That is correct, one render, one voice, but it means ~40 assertions across
10 test files pin the *old* strings and must be updated to the new prose:
`test_work_start_cli` · `test_mcp_server` · `test_broker` · `test_render_selection` ·
`test_contract_terminal` · `test_eval` · `test_gate_probe_cli` · `test_docs_probe_cli` ·
`test_issue_probe_cli` · `test_work_start_answer`. The plan enumerates each.

## Non-goals (sequenced elsewhere)

- **Structured/`--json` output** for machine consumers, prose is the M2 decision (the agent reads
  prose fine; M1 dogfood proved it). A structured mode is a later, separate slice if a consumer needs it.
- **Improving the engine's card-derivation copy** (`core/select.py` `render_*_claim` text/why), M2
  composes from the *existing* card fields in the render layer; it does not touch the pure core.
- **Legacy `refresh`/`context`/`why`/`open-source`**: that's Slice C.

## Design

### Component 1: the shared classification (`src/teamctx/assessment.py`)

Extract the *ready / heads-up / can't-verify* + stale-dep-vs-policy-gap logic out of `hook_signal`
into one pure module both renderers consume:

```python
CheckId = Literal["conflict", "criteria", "docs", "gate"]
CheckStatus = Literal["clear", "found", "unreachable", "not_configured"]

@dataclass(frozen=True)
class CheckState:
    check: CheckId
    status: CheckStatus
    cards: tuple[ContextCard, ...]   # the finding cards (status == "found"), else ()

@dataclass(frozen=True)
class WorkStartAssessment:
    kind: Literal["ready", "heads_up", "cant_verify"]
    checks: tuple[CheckState, ...]   # ordered conflict, criteria, docs, gate

def assess(answer: BrokerAnswer) -> WorkStartAssessment: ...
```

`assess` maps each of the 4 verdicts (label → `CheckId` via a fixed map) + its `Valuation` to a
`CheckStatus`: `"true"` → `clear`; `"false"` → `found`; `"unknown"` + `reason ==
"incomplete[stale-dep]"` → `unreachable`; `"unknown"` + `reason` starting `"incomplete[policy-gap]"`
(or anything else) → `not_configured`. Cards are grouped to their check by the card's `reason_code`
prefix (`collision.` → conflict, `criteria.` → criteria, `doc.` → docs, `gate.` → gate). `kind`:
any `found` → `heads_up`; else any **important** check (`conflict`/`gate`) `unreachable` →
`cant_verify`; else `ready`. (This is exactly today's hook logic, generalized to all four checks.)

### Component 2: `hook_signal` refactors onto `assess`

`hook_signal` calls `assess(answer)` and renders its single glanceable line from the
`WorkStartAssessment` (the hook still omits low-stakes gaps; behavior and its tests unchanged, the
output strings are identical, only the internal derivation moves to `assessment.py`).

### Component 3: the shared prose render (`contract_render.py`)

`render_broker_answer(answer)` builds the assessment and renders a signal-led prose report; the old
`render_selection` verdict-line/coverage/disclaimer rendering for the work-start path is replaced.
Structure:

```
<headline>                     # the signal
<finding / can't-verify bullets>   # heads_up / cant_verify only
<coverage line(s)>             # "Checked: … · … " and "Not checked: … (how to enable)"
<authority>                    # unchanged, only when present
```

**Headlines** (the render is multi-path, so it does not name a single file). As shipped:
- ready → `Looks clear to start.`
- heads_up → `Before you start, here is what to handle first:`
- cant_verify → `Heads up: I couldn't check the important things:`

**Per-(check, status) prose** the render composes (from existing card fields; never a raw reason code). As shipped:

| check | clear (in the Checked line) | found (a bullet) | unreachable | not_configured (in the Not-checked line) |
|---|---|---|---|---|
| conflict | "no open PRs touch your files" | `{card text}: look at it before you edit so you don't undo each other's work ({gh pr view N if parseable})` | "open PRs (couldn't reach GitHub)" | "open PRs (couldn't determine the repository)" |
| gate | "CI is green" | `{card text}: fix it or wait for a green build before relying on it` | "failing checks (couldn't reach GitHub)" | "failing checks (couldn't determine your branch)" |
| criteria | "the linked issue's criteria are unchanged" | `{card text}: re-check the criteria before you rely on them` | "spec changes (couldn't reach GitHub)" | "spec changes (no issue is linked to this branch; link one to enable)" |
| docs | "the docs you rely on are current" | `{card text}: rely on the current one instead` | "the docs you rely on (couldn't read the docs folder)" | "docs (no docs root is configured; set `work_start.docs_root` to enable)" |

**Coverage lines (honest, plain, shown in the *render*, omitted by the hook). Every check status is surfaced exactly once:**
- `clear` checks → one "Checked: …; …; …" line (for heads_up, "Also checked:").
- `found` checks → a bullet (above).
- `unreachable` important checks (conflict/gate) when `kind == cant_verify` → the can't-verify bullets,
  combined when both are down: "Open PRs and failing checks: teamctx couldn't reach GitHub. Either it
  has no access yet (run `teamctx install-hook` to connect it) or it's a temporary connection issue.
  Until it's back you won't see colliding PRs or red CI on your files."
- **Every other `unreachable` check** (non-important, or important when a found check already made it
  heads_up) → a "Couldn't check: …" line. This closes the honest-UNKNOWN hole: an unreachable check is
  never silently dropped behind a clean-looking headline.
- `not_configured` gaps → a "Not checked: … (how to enable)" line, surfaced plainly because the render
  is a deliberate read whose job is the honest-coverage picture (the hook omits these because it's an
  interrupt).
- The `gh pr view N` hint is **best-effort**: parse `#<digits>` from the card's `source_display`; omit if absent.

### Worked output (the three scenarios), as shipped

*ready:*
```
Looks clear to start.
  Checked: no open PRs touch your files; CI is green; the docs you rely on are current.
  Not checked: spec changes (no issue is linked to this branch; link one to enable).
```
*heads_up:*
```
Before you start, here is what to handle first:
  • PR #7 changes src/app.py: look at it before you edit so you don't undo each other's work (gh pr view 7).
  Also checked: CI is green; the docs you rely on are current.
```
*cant_verify:*
```
Heads up: I couldn't check the important things:
  • Open PRs and failing checks: teamctx couldn't reach GitHub. Either it has no access yet (run `teamctx install-hook` to connect it) or it's a temporary connection issue. Until it's back you won't see colliding PRs or red CI on your files.
  Checked: the docs you rely on are current.
  Not checked: spec changes (no issue is linked to this branch; link one to enable).
```

## Testing

- `tests/test_assessment.py` (new): `assess` maps each verdict/reason to the right `CheckStatus`;
  cards grouped to the right check; `kind` (found→heads_up; important-unreachable→cant_verify; else
  ready); via real `broker_answer` with crafted signals/statuses (the `test_hook_signal` pattern).
- `tests/test_render_selection.py` rewritten: assert the new prose (ready/heads-up/can't-verify
  headlines; plain per-check lines; no `UNKNOWN`/`NOT CLEAR`/`incomplete[...]`/`git_hosting` strings;
  gaps carry reason+fix).
- `tests/test_hook_signal.py`: unchanged behavior (hook output identical), should stay green after
  the refactor; adjust only if internal helper names change.
- **Update the rippled assertions** to the new prose: `test_work_start_cli`, `test_mcp_server`,
  `test_broker`, `test_contract_terminal`, `test_eval`, `test_gate_probe_cli`, `test_docs_probe_cli`,
  `test_issue_probe_cli`, `test_work_start_answer`. (The plan lists the specific assertions.)
- Full suite + ruff(src+tests) + mypy --strict green.

## To verify during implementation
- Whether `render_selection` is used anywhere besides the work-start path (it's exported); if the
  legacy `render_contract_context` path or a test needs the old behavior, keep `render_selection` and
  route only `render_broker_answer` to the new prose. `grep -rn render_selection src tests` first.
