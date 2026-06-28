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

**Headlines** (the render is multi-path, so it does not name a single file):
- ready → `Looks clear to start.`
- heads_up → `Before you start, worth handling first:`
- cant_verify → `Heads up, I couldn't check the important things:`

**Per-(check, status) prose** the render composes (from existing card fields; never a raw reason code):

| check | clear | found (bullet) | unreachable | not_configured |
|---|---|---|---|---|
| conflict | "no open PRs touch your files" | "An open PR ({#N if parseable}) already changes {paths}, look at it before you edit ({`gh pr view N` if parseable})." | "Open PRs: couldn't check, no GitHub access. Run `teamctx install-hook` to connect it; until then you won't see colliding PRs." | (rare, collision always runs) treat as unreachable copy |
| gate | "CI is green" | "A required check is failing on {paths}." | combined with conflict when both unreachable for the same cause → "Open PRs and failing checks: no GitHub access yet. Run `teamctx install-hook`; until then you won't see colliding PRs or red CI." | "Failing checks: not checked, couldn't determine your branch." |
| criteria | "the linked issue's criteria are unchanged" | "The spec moved: acceptance criteria on {issue} changed, re-check before relying." | "Spec changes: couldn't check, no GitHub access." | "Spec changes: not checked, no issue is linked to this branch (link one to enable)." |
| docs | "the docs you rely on are current" | "{doc} was superseded by {doc2}, rely on {doc2}." | "Docs: couldn't read the docs folder." | "Docs: not checked, no docs root configured (set `work_start.docs_root` to enable)." |

**Coverage lines (honest, plain, shown in the *render*, omitted by the hook):**
- The `clear` checks are summarized in one "Checked: … · … · …" line (for heads_up, "Also checked:").
- The `not_configured` (low-stakes) gaps go in a "Not checked: … (how to enable)" line, surfaced
  plainly because the render is a deliberate read whose job is the honest-coverage picture (the hook
  omits these because it's an interrupt). `unreachable` important checks are bullets (above), not here.
- The `#N`/`gh pr view N` hint is **best-effort**: parse `#<digits>` from the card's `source_display`;
  omit cleanly if absent.

### Worked output (the three scenarios)

*ready:* `Looks clear to start.` / `  Checked: no open PRs touch your files · CI is green · the docs you rely on are current.` / `  Not checked: spec changes, no issue is linked to this branch (link one to enable).`

*heads_up:* `Before you start, worth handling first:` / `  • An open PR (#7) already changes src/app.py, look at it before you edit (gh pr view 7).` / `  • The spec moved: acceptance criteria on issue #42 changed, re-check before relying.` / `  Also checked: CI is green; the docs you rely on are current.`

*cant_verify:* `Heads up, I couldn't check the important things:` / `  • Open PRs and failing checks: no GitHub access yet. Run \`teamctx install-hook\`; until then you won't see colliding PRs or red CI.` / `  Checked: the docs you rely on are current. Not checked: spec changes, no issue is linked to this branch.`

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
