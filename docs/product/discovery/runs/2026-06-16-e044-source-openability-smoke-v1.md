# E-044 Run: Source Openability Smoke V1

Date: 2026-06-16

Purpose: test whether source-body availability language improves `status_open` behavior on the collision and body-available paths.

## Scope

- Model: `sonnet` (`claude-sonnet-4-6` as reported by Claude Code).
- Runs: 2 total, context variant only.
- Source access: `status_open`.
- Scenarios: `primary-01-overlapping-file-change-v1`, `primary-02-changed-acceptance-criteria-v1`.
- Per-run cap: `$0.30`.

## Change Under Test

`status_open` prompts now include a `Source opening` section:

- source bodies are labeled `body available` or `body unavailable`,
- agents are told to open only body-available sources,
- same-file collision sources with unavailable bodies add a conservative patch note: preserve existing APIs or leave a review note when the missing body prevents a safe patch.

## Result

- Reported total cost: `$0.229188`.
- Quality: `1 pass`, `1 review`, `0 fail`.
- Collision scenario: review `7/8`, API preserved `yes`; remaining note was no validation command or test change.
- Jira scenario: pass `7/7`; agent opened `Jira API-482`, implemented changed criteria, added tests, and ran tests.
- Leak scan before each run: passed.

## Product Read

The prompt refinement appears directionally right. It changed the important failure mode from E-043: the collision scenario no longer rewrote the existing `rotate_token` API. It still did not validate, so this is not a clean quality win yet.

The body-available path still worked: the agent opened Jira and used the changed acceptance criteria.

Decision: keep source-openability language and run it against the larger slice before treating it as settled.

## Verification

- `python3 -m compileall -q src tests`: passed.
- `python3 -m pytest`: `56 passed`.
- `python3 -m ruff check .`: all checks passed.
- `python3 -m mypy src tests`: no issues in `20` source files.
- `git diff --check`: passed.
- `gitleaks dir --no-banner --redact .`: no leaks found.
