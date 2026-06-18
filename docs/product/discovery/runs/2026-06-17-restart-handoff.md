# Restart Handoff: TeamCtx And Codex Sandbox

Date: 2026-06-17

## Why Restart

Sandboxed shell commands in this Codex session still fail with:

```text
bwrap: Can't mount devpts on /newroot/dev/pts: Permission denied
```

Diagnosis:

- The container is running under Podman/rootless-style confinement.
- `bwrap --ro-bind / / /bin/true` works.
- `bwrap --dev-bind /dev /dev --ro-bind / / /bin/true` works.
- `bwrap --dev /dev --ro-bind / / /bin/true` fails because it tries to mount a fresh `devpts`.
- `codex sandbox --enable use_legacy_landlock /bin/true` works.
- After enabling the feature, `codex sandbox /bin/true` also works.

Persisted fix in `/home/eparenti/.codex/config.toml`:

```toml
[features]
memories = true
terminal_resize_reflow = true
use_legacy_landlock = true
```

This current Codex process appears to have already loaded the old bwrap backend,
so restart Codex. After restart, verify with a normal non-escalated tool call or:

```bash
codex sandbox /bin/true
```

Avoid running full `env`; an earlier attempt was rejected because it can expose
secrets. The useful narrow check was reading only `PATH` from `/proc/<pid>/environ`.

## Repo

TeamCtx repo:

```text
/home/eparenti/agents/repos/teamctx
```

Current git state before restart:

```text
## main...origin/main
 M tests/test_core_contracts.py
?? docs/product/discovery/fixtures/contracts/v0/issue-tracker-acceptance-criteria-document.json
```

## Current TeamCtx Work

User asked to pick back up on TeamCtx. The repo was clean on `main` at start.
Sprint 02 workstream 4 looked like the next repo-contained task: add one
fixture-backed issue-tracker scenario without claiming live Jira/Linear support.

Added fixture:

```text
docs/product/discovery/fixtures/contracts/v0/issue-tracker-acceptance-criteria-document.json
```

Purpose:

- Model Jira `API-482` as fixture-backed structured issue metadata.
- Signal that acceptance criteria changed after branch start.
- Keep issue body/comments closed.
- `open-source` target is `status_only`, not source text.
- No live Jira/Linear connector claim.

Modified test:

```text
tests/test_core_contracts.py
```

Added:

- `ISSUE_CONTRACT_FIXTURE`
- `load_issue_contract_fixture()`
- `test_issue_tracker_contract_fixture_is_status_only_structured_metadata()`

Current test asserts:

- The fixture round-trips through Core Contract V0.
- The signal source family is `issue_tracker`.
- No guidance records are emitted.
- The card is fresh/high confidence/status-only.
- The source-open target is status-only and cannot include source text.
- The policy reason mentions comments.

## Important Caveat

The new test may currently fail because the fixture target policy reason says:

```text
The fixture proves source status and structured metadata without exposing issue body text.
```

but the test checks:

```python
assert "comments" in target.policy.decision_reason
```

Either update the fixture target `decision_reason` to mention comments, or relax
the assertion. Product intent is to explicitly prove arbitrary issue comments are
out of scope, so the better follow-up is probably to update the fixture text.

## Next Steps After Restart

1. Confirm sandbox works without escalation:

```bash
pwd
git status --short --branch
```

2. Fix the likely policy-reason/test mismatch if present.

3. Run focused verification:

```bash
python3 -m pytest tests/test_core_contracts.py tests/test_contract_terminal.py -q
python3 -m ruff check tests/test_core_contracts.py
```

4. Add terminal renderer/CLI tests for the new fixture if continuing workstream 4:

- `context --contract ...issue-tracker...` renders the `Needs attention` card.
- `why card_issue_acceptance_changed --contract ...` explains linked issue and status-only body.
- `open-source card_issue_acceptance_changed --contract ...` keeps source body unavailable/status-only.

5. Add a short discovery run/experiment note for the fixture-backed issue path,
and update Sprint 02 workstream 4 checkpoint if the tests pass.

6. Finish with:

```bash
git diff --check
python3 -m pytest -q
python3 -m ruff check .
python3 -m mypy src tests
```

Full suite has not been run after these changes.
