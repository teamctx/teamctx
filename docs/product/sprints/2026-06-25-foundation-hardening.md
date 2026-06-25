# Foundation Hardening — one model, valid evidence engine, clean seams

*Started 2026-06-25. This is the ONE plan in flight (supersedes CURPLAN3/MCP until done).
Each section below is a self-contained chunk: if context compacts, any single chunk is
actionable on its own. Read [the mandate](#0-the-mandate) first, every session.*

---

## 0. The mandate

**Bounded mode: constraints OFF, make the foundation excellent, then resume normal
discipline.** Edgar's call (2026-06-25): we stop forward motion (MCP, distribution, breadth)
and make the base something we'd stand behind unconditionally. We do not weigh cost, time,
or scope against "excellent" during this phase. *After* the foundation is rock-solid, the
constraint hats go back on.

**What "excellent" means here (the bar, and the anti-rat-hole guardrail):** the foundation
**fully embodies the product's own thesis** — *one model, an evidence engine that tests the
real engine, clean build-once seams, credibility true by construction.* It does **not** mean
infinite polish. The thesis is the bar, not abstract code-beauty. If a change doesn't make
the foundation more truly embody the thesis, it's out of scope for this phase.

**The thesis (what the foundation must embody):** deterministic, no-LLM, read-only broker;
facts arrive verbatim, source-backed, verifiable; the broker never false-clears; claims
never outrun proof.

---

## 1. The north star (target end-state)

**One model.** The `core/contracts.py` Pydantic model is the only model. The prototype model
(`core/models.py`, `core/cards.py`) is deleted. Every consumer — connectors, CLI, MCP, and
the evidence engine — speaks the contracts model.

**One broker entry point.** A single `broker_answer(request, signals, statuses, declarations)
→ BrokerAnswer{selection, verdicts}` in core. The verdict loop leaves `cli.py`. CLI, MCP, and
eval all call this one function. A `compose()` merges N connector documents into one input.

**Target file topology** under `src/teamctx/`:
- `core/` — thesis engine ONLY: `contracts.py`, `prop.py`, `evaluate.py`, `snapshot.py`,
  `authority.py`, `severity.py`, `coverage.py` (extracted), `kinds.py` (the 4 CardKinds,
  self-contained), `broker.py` (compose + select + broker_answer). No `models.py`, no
  `cards.py`, no `fixtures.py`.
- `connectors/` — each connector + `_contract.py` (shared policy/status/unavailable/slug
  helpers, used by all).
- `eval/` (new) — the evidence engine, rebuilt on the real engine: scenarios in the
  contracts model, the "context" variant rendered from REAL derived cards, plus the kept A/B
  campaign machinery.
- `cli.py` — commands on the real model; eval commands delegate to `eval/`.
- `contract_render.py`, `contract_documents.py`, `project_config.py` — unchanged role.

---

## 2. Disposition of every Model B file (decided, grounded in a full read)

| File | Disposition | Why |
|------|-------------|-----|
| `core/models.py` | **DELETE** | prototype types; concepts re-expressed in contracts model |
| `core/cards.py` | **DELETE** | prototype selection (select_cards, tag/visibility affordances) |
| `core/fixtures.py`, `fixtures.py` | **DELETE** | fixture loaders; replaced by contracts-model eval Scenario |
| `render.py` | **DELETE** card-render; **MOVE** prompt-construction to `eval/` re-pointed at real cards | real renderer is `contract_render.py`; uses prototype `card.source` field |
| `context.py` | **DELETE** | pure prototype selection wrappers |
| `source_open.py` | **DELETE** | real equivalent `render_contract_open_source` exists |
| `why.py` | **DELETE** | real equivalent `render_contract_why` exists |
| `session.py` (`SessionSelection`) | **DELETE** prototype; session concept already typed as `SessionContextUse` in contracts | not on product path; rebuild on real type only if/when needed |
| `benchmark.py` | **REBUILD in `eval/`** | keep A/B campaign machinery (run-sheets, randomized order, score-sheet); re-point input to real cards |
| `claude_benchmark.py` | **REBUILD in `eval/`** | keep disposable-repo runner + run capture; re-point context variant to real cards |
| `claude_quality.py` | **MOVE to `eval/`** | run-artifact quality assessment; largely model-agnostic |

**CLI commands:** `context` / `why` / `open-source` already have `--contract` (real-model)
branches — **drop the `--fixture` branch, keep the command.** `use` and `benchmark-prompt`
are prototype-only — **delete** (session affordance covered by `SessionContextUse` if revived).
`benchmark-export` / `claude-agent-benchmark` / `claude-agent-assess` — **delegate to `eval/`**.

---

## 3. Advisor feedback assessment (Gemini 2.5 Pro, as referee)

Edgar's rule: advisors advise me; I decide what we value. My ruling on the referee pass:

- **VALUED — kept.** It elevated the dual-model problem from my too-soft "relocate + flag"
  to "fix the model before building MCP." That correction is right and reshaped this plan.
- **OVERRIDDEN — its severity framing.** It claimed "the thesis is unproven / no evidence the
  engine works." Overstated. Soundness IS tested against the real engine (212 tests, fail-
  closed validators, purity, the `evaluate` under-approximation). Usefulness HAS live dogfood
  evidence against the real engine (collision, red-CI, criteria-changed). The accurate
  statement: the **repeatable/automated** usefulness eval is disconnected. We act on the
  sharpened priority, not the overstated severity.
- **REJECTED — its tactical suggestion.** "MCP concatenates JSON as a temp hack to avoid
  polluting core." Against the mandate (excellent, not temp hacks) and against build-once: the
  compose seam goes in core, built right. Its own reasoning (don't pollute core) argues for
  this, not for the hack.

Net: the referee earned its keep by forcing a priority correction; I'm overriding its severity
claim and its tactic. Recorded so we don't re-litigate.

---

## 4. The phases (build-once order; green at every step)

Discipline that holds even with constraints off: **the tree stays green at each phase**
(tests + ruff + mypy strict + the core purity test). Green-at-each-step is correctness, not a
cost concern. Each phase names whether it is **behavior-preserving** (golden output unchanged)
or **behavior-changing** (new golden).

### Phase 1 — The broker entry point + compose seam *(behavior-preserving)*
Build the seam everything hangs on, first, because the new `work-start` AND the rebuilt eval
both consume it.
- `compose(documents) → merged (signals, statuses, open_targets, guidance)`.
- `BrokerAnswer = {selection, verdicts}`; `broker_answer(request, signals, statuses,
  declarations)`. Move the verdict loop out of `cli.py` (`_work_start_view`) into `core/broker.py`.
- Probes call `broker_answer`; output **byte-identical** to today (golden-guarded).
- **Done-gate:** one broker entry point; cli probes delegate to it; all golden outputs
  unchanged; green.

### Phase 2 — Unified `work-start` *(behavior-changing: new golden)*
Make the flagship command real: run all connectors, not just collisions.
- A connector-runner: given config (repo, token, paths, issues, since), run every applicable
  connector, return their documents.
- `work-start` = run-all → `compose` → `broker_answer` → render. Now it actually checks
  collisions + issues + docs + gates in one call.
- **Done-gate:** `work-start` surfaces all four kinds and honest coverage in one call;
  verdicts reflect real cross-source coverage; green; dogfooded once on this repo.

### Phase 3 — One model (kill the prototype) *(behavior-changing where prototype CLI dies)*
Now that the real broker entry point exists, re-point eval at it and delete the prototype.
- Create `eval/`; move `benchmark.py`, `claude_benchmark.py`, `claude_quality.py` in.
- Replace `Fixture(expected_cards)` with an eval **Scenario** in the contracts model
  (`RequestContext` + `SourceSignal`s + `SourceStatus`es + disposable repo). The "context"
  prompt variant renders the **real derived cards** via `broker_answer` / `contract_render`.
  Keep the A/B machinery (baseline vs context, randomized order, run/score sheets).
- Drop `--fixture` branches; delete the prototype files per §2; fix `core/__init__.py` to
  export only thesis types.
- **Done-gate:** `grep core.models|core.cards` returns nothing; the prototype model classes do
  not exist; eval consumes the real engine; green.

### Phase 4 — Engine internal excellence *(behavior-preserving)*
Within-core cleanup now that one model reigns.
- Extract connector boilerplate → `connectors/_contract.py` (`metadata_only_policy`,
  `source_status`, `unavailable_document`, `slug`).
- De-duplicate the four `render_*_claim` functions into a shared skeleton + per-kind text,
  **byte-identical preserving** (golden-guarded). Do NOT over-consolidate the `derive_*`
  functions — the matching IS the relevance logic; explicit is safer.
- Optional, held loosely: split `select.py` into `kinds.py` (the 4 kinds) + `broker.py`
  (engine mechanics) if it improves comprehension. Tighten loose types (`CardKind.signal_type`
  → `SignalType`).
- **Done-gate:** duplication removed; core reads clean; all golden outputs unchanged; green.

### Phase 5 — Validate the foundation
Prove it's rock-solid, then stop (the full research campaign is NOT foundation — see §6).
- Run the rebuilt eval **end-to-end on ≥1 real scenario** against the real engine; produce
  real run artifacts. This proves the wiring is valid (not the statistical study).
- Full conformance green: tests, ruff, mypy strict, purity, golden/replay.
- Wire (not necessarily run-at-scale) the **E4/E5** measurement harness on the contracts model
  (false-`Unknown` rate; consumer false-clear rate — the open obligation from protocol v1.2).
- **Done-gate:** the eval demonstrably tests the REAL engine end-to-end; foundation green and
  conformant; we'd stand behind it unconditionally.

---

## 5. Invariants (must hold throughout every phase)
1. **Green at each step** — tests + ruff + mypy strict + core purity test.
2. **Never false-clear** — `evaluate` stays a sound under-approximation; absence ≠ all-clear.
3. **Observable preserved unless deliberately changed** — golden tests guard byte-output;
   behavior-changing phases (2, parts of 3) get new goldens on purpose.
4. **Existence-privacy holds** — the digest binds only the P-visible projection.
5. **One model** — after Phase 3, no code imports a non-contracts model type.

## 6. Explicit scope boundary (so "no matter what" doesn't become a research study)
**IN (foundation, now):** one model; eval wired to the real engine and proven to run
end-to-end; clean seams; soundness conformance green.
**OUT (later, normal-constraint mode):** the full benchmark *campaign* / statistical
usefulness result; E4/E5 numbers measured across a corpus; severity-constant calibration; MCP;
breadth (Jira/Confluence/GitLab/L-tier). The foundation requires the evidence engine to be
VALID and RUNNABLE — not to have RUN the whole study.
