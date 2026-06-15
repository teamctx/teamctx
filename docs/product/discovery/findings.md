# Discovery Findings

Updated: 2026-06-15

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
- Run the first external model pilot using the response path convention in
  `runs/2026-06-15-e029-primary-benchmark-export/score-sheet.csv`.
- Defer real connectors until benchmark evidence supports the context surface.
- If language remains contested, run the E-011 language variant track on three
  scenarios before the full benchmark.
