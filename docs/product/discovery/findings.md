# Discovery Findings

Updated: 2026-06-16

## Current Product Thesis

TeamCtx should provide working context at agent-terminal start and resume points.
The user should not have to learn TeamCtx vocabulary or manage a separate
knowledge system.

## Emerging Decisions

- Ambara is R&D input, not the product surface.
- The first product surface is a terminal context block, not a dashboard.
- Internal packets are experiment scaffolding; user-facing context must be plain.
- Broad source integration is a trap until manual source probes prove signal.
- Chat is explicit handoff only, never broad chat mining.
- Source health is part of context; missing context is not a green light.
- `Use now` is too vague for a primary action.
- Not every omission deserves a card; silent omission is often the safest UX.
- User-facing omissions should appear only when they change confidence for a
  configured source in the current scope.
- Product surfaces should be separated into working context, explanation, and
  source status/settings.
- Some source facts belong in a hard `Never show` category, not merely hidden
  behind another view.
- Benchmarks should use provisional language and preserve a language-variant
  track, so naming uncertainty does not block measurement.
- Benchmark scenarios must not simply give the answer; they should expose a
  task-changing signal and leave room for the agent to reason or verify.
- The first benchmark should run six primary scenarios: overlapping work,
  changed acceptance criteria, stale process doc, safety-blocked source change,
  inaccessible linked docs, and revised project guidance.
- Source planning should start from source signals, not connector count. Launch
  sources should produce scoped task-changing signals and safe failure states.
- First source candidates: local workspace, GitHub/GitLab metadata,
  Jira/issue-tracker metadata, configured or linked docs, and approved local
  note folders. CI/deploy is the next probe; broad chat/email/search are not
  first-product surfaces.
- Source fixtures suggest the backend should start with source signals, not
  generic memory records. The rendered context card is a view over a scoped
  signal.
- `approved_guidance` should be separated from `advisory_match`; approved local
  notes can be useful without being authoritative project guidance.
- User-facing context should avoid `approved note`; use `selected folder` or a
  concrete source name for advisory local-note matches. Reserve `Project
  guidance` for reviewed, scoped guidance only.
- The first durable contract should be `SourceSignal`, `GuidanceRecord`,
  `SessionContextUse`, and `SourceStatus`; rendered context cards are views over
  these objects.
- Product/package boundary should be one product with two layers: public
  `teamctx` plus a non-user-facing `teamctx-core`. Ambara survives as R&D input,
  not as a separate product dependency.
- First vertical slice should be an issue-backed file edit with changed context:
  local workspace scope, Git host collision, issue changed-since-start, optional
  reviewed guidance, stale source caveat, terminal rendering, `Show why`, and
  `Use in this session`.
- Build the first slice with fixtures before real connectors; the first real
  connector candidate should be GitHub/GitLab metadata for file collision.
- Prototype plan should start with one JSON fixture and four commands: render
  context, show why, use an advisory card in session, and generate benchmark
  prompt. Advisory note cards should not be agent-visible by default.
- Repo fit assessment says to keep the first durable-core boundary inside
  `src/teamctx/core/`; do not create a separately installable `teamctx-core`
  package until the fixture-backed loop proves value.
- Existing artifact/relationship/card architecture can map cleanly to the new
  signal model: artifacts feed relationships, relationships produce source
  signals, and signals render context cards.
- Implementation spike should be fixture-backed inside `src/teamctx/core/`, with
  no live connectors, no package split, and no memory/ledger/registry language.
- Golden outputs now define the prototype's trust boundary: advisory note cards
  are omitted by default and included only after explicit session use.
- Relevance gates must be separate from visibility gates: a card can be safe to
  render and still irrelevant to the current task. Stale source-health caveats
  should appear only when they change confidence for the task scope.
- Context rendering should group cards under each section heading once. Repeated
  section headings make the terminal output feel noisier than the actual signal
  count.
- The fixture-backed prototype is now executable. It renders default working
  context, explains cards with `Show why`, supports session-only advisory
  context, and generates benchmark prompts from the same fixture.
- Implementation verification passed: compileall, pytest, ruff, mypy, and CLI
  smoke tests for context, why, use, and benchmark prompt.
- The six primary E-014 benchmark scenarios are now executable fixtures. The CLI
  can generate baseline/context prompts from any fixture without hard-coded
  scenario logic.
- The six primary benchmark prompt pairs are now exported into a ready-to-run
  packet with a run sheet, generated by `teamctx benchmark-export` from the
  executable fixtures.
- The generated benchmark packet now includes alternating run order,
  `manifest.json`, and `score-sheet.csv`; it is ready for real model execution
  without prompt hand-editing.
- The E-035 Claude runtime benchmark does not support a blanket token-savings
  claim. TeamCtx saved work on fresh direct-signal scenarios and cost more when
  default context behaved like source-health warning.
- Agent prompt context is now gated separately from rich context inspection:
  fresh task-changing cards and active project guidance can enter by default,
  while stale, unavailable, and blocked source-health cards require explicit
  selection or a relevance path.
- E-037 targeted Claude rerun confirms prompt gating reduces old
  warning-context overhead, but does not beat baseline while broad local source
  snapshots remain exposed. The token-savings product lever is source access
  routing plus prompt gating, not prompt gating alone.
- The benchmark harness now needs source-access variants. E-038 adds a
  `full` versus `none` source access control so future runs can isolate prompt
  context from broad source browsing.
- E-039 source-access `none` was the first strong cost-saving benchmark
  result on the warning scenarios: cheaper than E-035 baseline and E-037
  gated/full-source context with pass-level quality. But total source absence
  loses useful source-health caveats, so the next product shape is status-only
  routing, not hiding sources completely.
- E-040 status-only source routing is the best current default candidate:
  compact stale/unavailable/blocked source status reaches the agent, but source
  bodies are not exposed as a browsable workspace by default.
- E-041 defines the source-body escape hatch: source bodies open only by explicit
  action, one source at a time, after policy checks. Blocked and unavailable
  sources do not render body text, even if fixture data contains it.
- E-042 benchmarked that escape hatch: `status_open` opened only `Jira API-482`,
  preserved pass-level quality, added tests, and cost less than full source on
  the changed-acceptance-criteria scenario.

## Provisional Language Set

Use these defaults in the next benchmark unless CPO feedback changes them:

- Container: `Working context`
- Temporary action: `Use in this session`
- Future action: `Draft guidance`
- Saved/approved section: `Project guidance`
- Explanation action: `Show why`
- Source caveat action: `Continue without it`

## Stronger Language Candidates

- `Needs attention`
- `Good to know`
- `Verify before relying`
- `Use in this session`
- `Draft guidance`
- `Hide for this session`
- `Show why`
- `Suggest update`

## Risky Language Candidates

- `Keep for future`: may sound like memory or tracking.
- `Saved for this project`: may sound too permanent or document-like.
- `Review required`: accurate, but may feel heavy.
- `Use as background`: honest, but weak.
- `Use now`: vague unless behavior is defined.
- `Pin for this session`: accurate, but sounds too UI-ish for the leading
  terminal action.

## Action Model Candidate

Use a small set of actions with explicit consequences:

- `Use in this session`: temporary context, visible to the agent now, expires
  with the session.
- `Draft guidance`: editable future candidate, scoped, inactive until reviewed
  or accepted.
- `Hide for this session`: suppress valid context without muting the source or
  deleting guidance.
- `Open source`: inspect the original artifact without changing agent context.
- `Show why`: explain source, scope, freshness, and status.
- `Suggest update`: create an update draft for saved guidance.
- `Continue without it`: proceed with an explicit stale/unavailable caveat.

## Surface Model

- `Working context`: automatic or on-demand task-changing context shown in the
  agent terminal. Alternate under test: `Context for this task`.
- `Show why`: on-demand explanation of source, scope, freshness, status, and
  agent visibility.
- `Source status/settings`: admin or diagnostic source configuration and health.
- `Never show`: content that should not appear in normal product surfaces,
  including DMs, private note matches, credential-shaped text, prompt-injection
  instructions, inaccessible artifact details, unknown field values, and
  productivity/presence/sentiment signals.

## Safety Surface Rules

- Private, personal, scratch, secrets, DM, unmarked chat, and unknown-field
  omissions are silent in normal working context.
- Omission becomes visible only when it changes confidence for a configured
  source in the current task scope.
- Inaccessible artifacts are described in aggregate, never by title or URL.
- Safety blocks should not name exact sensitive patterns in normal UI.
- Stale source content can create a warning, but not guidance.
- Eligible chat requires both an allowlisted place and an explicit marker.
- Identity is minimized by default, even for eligible chat handoffs.

## Benchmark Readiness

Ready for first manual paired run:

- Overlapping file change.
- Changed acceptance criteria.
- Stale process doc.
- Safety-blocked source change.
- Inaccessible linked docs.
- Revised project guidance applies.

Secondary benchmark scenarios:

- Revised explicit chat handoff.
- Revised vault note advisory.

Do not run chat/vault first unless source-family breadth becomes the immediate
question; they are valuable, but less central than the first six.


## Benchmark Response Capture

The generated benchmark packet now has a response path convention and result
capture notes. `score-sheet.csv` points each scenario to baseline and context
answer files under `responses/{model}/...`, and `results/README.md` keeps
scoring definitions beside the packet.

This makes the first external model pilot operationally ready without adding
connector or backend commitments.


## OpenRouter Smoke Pilot

The first real paired benchmark run used `primary-01-overlapping-file-change-v1`
against two OpenRouter models. `openai/gpt-5.4-mini` showed a positive context
effect: it paused for same-file PR evidence before editing. `openai/gpt-5.5`
did not provide a clean signal because the context response emitted pseudo
terminal/tool-call text and hit the completion-token cap.

Product conclusion: working context can change behavior in the desired
direction, but the benchmark must distinguish chat-answer evaluation from
actual agent-terminal execution before full-packet scoring.


## Claude Agent Runtime Pilot

The first Claude Code runtime benchmark on `primary-01-overlapping-file-change-v1`
showed a positive economics signal: the TeamCtx context variant used one fewer
turn, one fewer tool call, one fewer file read, about 5.2 fewer seconds, and
about 38% lower reported cost than baseline.

The quality signal is mixed. Baseline found the same PR evidence by lookup and
made a conservative additive helper; context used the PR evidence sooner and did
less work, but modified the existing function directly. Future scoring must
separate economics, risk awareness, and patch quality.


## Claude Quality Scoring

The first deterministic quality scorer confirms that E-033 should be treated
as a positive economics signal, not a full quality win. Baseline scored 7/8
and context scored 6/8. Both were marked `review` because neither captured a
validation attempt; the context run also changed the existing `rotate_token`
API in the same-file collision scenario.

The benchmark now separates runtime economics from patch quality. This is the
right shape for the Ambara-era savings claim inside TeamCtx: prove saved lookup
work and cost, then prove quality is preserved or improved.


## Claude Six-Scenario Runtime Benchmark

The six-scenario Claude Code runtime benchmark produced a mixed but useful
product signal. TeamCtx context reduced cost and tool work on the two strongest
direct-signal scenarios: same-file PR collision and changed acceptance criteria.
Across all six scenarios, context cost more overall: baseline total reported
cost was `0.8382276`; context total reported cost was `0.9118254`.

Quality was acceptable after task-aware scoring: `8 pass`, `4 review`, `0 fail`.
The product claim should not be blanket token savings. The sharper claim is
that TeamCtx saves lookup work when context is fresh, specific, and task-changing;
warning/source-health context may add cost to preserve safety or completeness.

## Source Status Only Benchmark

E-040 tested the middle source-routing mode against the three warning scenarios:
no `source-snapshots/` tree, but compact source status in the prompt when stale,
blocked, or unavailable source state changes confidence.

The result was the strongest product shape so far. Status-only cost `$0.282821`
across the three warning scenarios, versus `$0.287766` for no source,
`$0.354957` for E-035 baseline, and `$0.447406` for E-037 gated/full source.
Quality stayed at `3 pass`, `0 review`, `0 fail`.

The behavior also improved. Scenario 3 drafted from local files while clearly
marking the stale Confluence risk. Scenario 4 blocked on safety-filtered Jira
status. Scenario 5 blocked on inaccessible linked docs. That is the product
promise in plain terms: TeamCtx should save lookup work without letting missing
or stale evidence masquerade as confidence.


## Source Open On Demand Contract

E-041 added the missing companion to status-only routing: an explicit source-open
path. Fixtures can now carry optional source bodies, but those bodies are not
part of default working context or agent prompts.

The prototype command is `teamctx open-source <card-or-source-id>`. It resolves a
single source, checks policy, shows stale caveats before body access, and refuses
to render blocked or unavailable bodies. The safety test intentionally included a
blocked source body in fixture data and verified that it did not print.

This keeps the product shape honest: TeamCtx can save lookup work by opening the
one source that matters, without returning to the expensive E-037 pattern where
all source snapshots become a browsable workspace.


## Source Open On Demand Benchmark

E-042 compared full source access with `status_open` on the changed acceptance
criteria scenario. Full source passed, but it browsed the source tree and read an
extra GitHub PR snapshot after reading Jira. Status open passed by opening only
`Jira API-482` through `.teamctx/open_source.py`.

Status open cost `$0.175604` versus `$0.210772` for full source, a `-$0.035169`
reported-cost delta on the one-scenario smoke. It used more turns and Bash
commands because source opening is explicit, but it read fewer files, added tests,
and preserved pass-level quality.

This moves the default candidate from plain status-only to status-only plus
open-on-demand. Compact context should tell the agent what changed confidence;
open-on-demand should provide the one source body that matters when compact
context is not enough.


## Open Product Questions

- Is `Working context` better than `Context for this task` as the container label?
- Is `Draft guidance` understandable outside our heads?
- What is the lightest possible review path for solo users and small teams?
- Should out-of-scope absence be silent by default?
- Should omitted/private source notices appear only in source health views?
- Does `Use in this session` feel right as the leading temporary-context action?
- Does `Draft guidance` feel right as the future-context action?
- Is `Project guidance` better than `Saved for this project` for approved
  scoped guidance?
- What exact context packet does a session action add to the agent prompt/context?
- How often should access-limited source warnings appear before they become
  noise?
- What is the lightest open-on-demand path for source bodies when compact status
  is not enough?
- Should the user-facing label be `Open source`, `Open original`, or something
  more concrete like `Open PR` / `Open issue`?

## Next Experiments

- Run E-004 language with CPO feedback.
- Run E-005 red-team fixtures before any connector work.
- Run E-011 benchmark pack v2 using the six primary scenarios and provisional
  language.
- Run E-014 first benchmark run kit against at least one daily-driver model and
  one stronger reasoning model.
- Build source fixtures for E-015 launch/probe source families.
- Test `advisory_match` versus `approved_guidance` language before modeling
  local notes or docs as authoritative.
- Carry E-017 authority split into source-signal data model sketches.
- Sketch the first vertical prototype around local workspace, Git hosting, issue
  tracker signal, terminal rendering, `Show why`, and `Use in this session`.
- Turn E-020 into a fixture-backed prototype build plan with command names and
  minimal CLI flow.
- Inspect existing `teamctx` package shape and decide how to fit the fixture
  prototype without overbuilding.
- Create a small implementation spike plan for `src/teamctx/core/` and CLI
  golden tests, but do not start connector work.
- Run E-014 benchmark packet from
  `runs/2026-06-15-e029-primary-benchmark-export/` against at least one
  daily-driver model and one stronger reasoning model, using `run-order.md` and
  `score-sheet.csv`.
- Carry E-025 relevance gates into any prototype implementation.
- Get CPO read on `Use in this session`, `Draft guidance`, `Saved for this
  project`, and `Working context`.
- Record first manual paired benchmark results before connector or backend build
  planning.
- Design context-gating rules that separate default prompt context from source-health
  or `show why` context before building real connectors.
- Defer real connectors until benchmark evidence supports the context surface.
- If language remains contested, run the E-011 language variant track on three
  scenarios before the full benchmark.
- Extend status-only source routing to the full six-scenario benchmark or one
  larger daily-driver task set.
- Run `status_open` on a larger benchmark slice, starting with the full six
  primary scenarios or a smaller set that includes both direct-signal and
  source-health tasks.
- Decide whether source opening should be an agent command, an MCP read-only
  tool, or both for the first real product surface.
