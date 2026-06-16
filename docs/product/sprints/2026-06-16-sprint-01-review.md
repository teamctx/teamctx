# Sprint 01 Review

Dates: 2026-06-16 through 2026-06-29
Review date: 2026-06-16

## Sprint Goal

Prove that TeamCtx can move from benchmarked fixture behavior to a narrow real
vertical slice without losing the product boundary.

## Outcome

Achieved for Sprint 01 scope.

TeamCtx now has:

- stricter benchmark scoring for source-openability, collision behavior, and
  validation;
- Core Contract V0 for source signals, source status, source-open targets,
  guidance, session use, request context, policy, and context cards;
- a narrow GitHub PR metadata probe;
- contract-backed terminal commands: `refresh`, `context`, `why`, and
  `open-source`;
- project config for the demo path;
- product language docs and a scripted terminal transcript;
- a live GitHub overlapping-PR proof against public PR metadata.

## Workstream Review

### Workstream 1: Benchmark And Product Contract

Status: complete.

Evidence:

- E-045 ran `status_open` across all six primary scenarios.
- Result: four pass, two review, zero fail.
- Collision behavior now distinguishes preserving API, changing API, blocking,
  and unclear behavior.
- Validation scoring no longer treats source-opening commands as validation.

Decision:

Keep compact source status by default with policy-gated source opening on demand.

### Workstream 2: Core Contract V0

Status: complete.

Evidence:

- `src/teamctx/core/contracts.py` implements versioned V0 contracts.
- Golden fixture: `docs/product/discovery/fixtures/contracts/v0/core-contract-document.json`.
- Tests reject unknown fields, hidden agent-visible signals, blocked source text,
  draft guidance to agent, and project-guidance cards without guidance refs.
- File-backed loading moved outside pure core.

Decision:

Future connectors normalize into Core Contract V0. They do not emit rendered cards
directly.

### Workstream 3: First Live Source Family Probe

Status: complete for GitHub PR metadata.

Evidence:

- `teamctx github-pr-probe` and `teamctx refresh` fetch GitHub open PR metadata
  and changed paths.
- Missing token/API errors produce source status.
- E-051 produced a live overlapping-file card from public GitHub PR metadata.

Exclusions preserved:

- no comments;
- no review bodies;
- no raw patches;
- no commit bodies;
- no author identity;
- no broad repo search.

### Workstream 4: Terminal Vertical Slice

Status: complete for the Sprint 01 demo path.

Evidence:

- `teamctx refresh` writes `.teamctx/context.json` by default.
- `teamctx context --contract ...` renders working context and relevant source
  status.
- `teamctx why ... --contract ...` explains source, reason, scope, freshness,
  confidence, source-body state, and agent visibility.
- `teamctx open-source ... --contract ...` is read-only and keeps status-only
  targets closed.
- E-050 captures the scripted terminal demo.

### Workstream 5: Product Language And Docs

Status: complete.

Evidence:

- `docs/product/language-memo.md` records the user-facing language set.
- README now describes the first runnable terminal slice.
- E-050 captures a transcript.

Language decisions:

- keep `Working context`;
- keep `Show why`;
- keep `Open source` for Sprint 01, with a note that it may become `Open PR`,
  `Open issue`, or `Open doc`;
- avoid memory, ledger, registry, promotion, source signal, authority tier, and
  durable-core language in user-facing surfaces.

## Verification

Latest full verification before review:

```bash
python3 -m compileall -q src tests
python3 -m pytest -q
python3 -m ruff check .
python3 -m mypy src tests
git diff --check
gitleaks dir --no-banner --redact .
```

Result at review time:

- tests: 87 passed
- Ruff: passed
- mypy: passed
- diff check: passed
- gitleaks: no leaks found

## Remaining Risks

- GitHub live proof used a public repo because `teamctx/teamctx` had no open PRs
  at run time. That is acceptable for proving the connector path, but the next
  demo should use an owned repo with a known open PR.
- There is still no Jira, Confluence, Obsidian, Slack, GitLab, or Linear live
  connector. This is intentional.
- The terminal flow is useful but still early: config is JSON-only and there is
  no guided setup command yet.
- Source body opening is status-only for the GitHub metadata probe. That is the
  correct Sprint 01 safety boundary, but later source-family-specific open
  actions will need design.

## Next Sprint Recommendation

Sprint 02 should focus on demo reliability and one owned-repo dogfood loop:

1. Add `teamctx init` for `.teamctx/config.json`.
2. Run the GitHub probe against an owned repo with a seeded open PR.
3. Add a small local cache so `context`, `why`, and `open-source` default to
   `.teamctx/context.json` without repeated `--contract` flags.
4. Add one issue-tracker fixture path, but do not add a live Jira connector yet.
5. Decide whether `open-source` should split into `open-pr`, `open-issue`, and
   `open-doc`.
