# E-043 Run: Status Open Six Primary V1

Date: 2026-06-16

Purpose: compare `status_open` against prior full-source and status-only Claude Code runs across the full six primary benchmark scenarios.

## Scope

- Model: `sonnet` (`claude-sonnet-4-6` as reported by Claude Code).
- Runs: 6 total, context variant only.
- Scenarios: all six primary benchmark fixtures.
- Source access: `status_open`.
- Per-run cap: `$0.30`.

The benchmark was rerun after hardening the helper: `.teamctx/open_source.py` remains visible in the disposable workspace, but source payload data is not written into the workspace and is provided through `TEAMCTX_SOURCE_OPEN_DATA`. This is still a benchmark stand-in, not the final product boundary.

## Result

- Reported total cost: `$0.788972`.
- Full-source comparison total: `$0.911825`.
- Delta versus full source: `-$0.122854` (`-13.5%`).
- Quality: `5 pass`, `1 review`, `0 fail`.
- Review: `primary-01-overlapping-file-change-v1` changed the existing `rotate_token` API in the same-file collision scenario.
- Leak scan before each run: passed.

## Aggregate Comparison

| Metric | Full source | Status open | Status open delta |
| --- | ---: | ---: | ---: |
| Reported cost | `0.911825` | `0.788972` | `-0.122854` |
| Turns | `60` | `49` | `-11` |
| Tool calls | `54` | `43` | `-11` |
| Files read | `35` | `21` | `-14` |
| Bash commands | `6` | `13` | `7` |

## Product Read

`status_open` is a better shape than full source snapshots: less aggregate cost, fewer turns, fewer tool calls, and fewer files read. It also avoids making source bodies browsable by default.

It is not a blanket replacement for status-only. On stale/blocked/unavailable warning scenarios, status-only cost `$0.282821` while status-open cost `$0.308976`. The extra source-opening surface can create useful checks, but it can also add tool calls just to learn that a body is unavailable.

The product stance after E-043: compact source status should remain the default; open-on-demand should exist when a source body is available and materially useful. Agents should not have to discover body availability by trial and error.

## Behavioral Notes

- Scenario 2 opened `Jira API-482`, implemented the changed acceptance criteria, and ran tests.
- Scenario 3 opened the stale Confluence source, received only status/caveat information, and updated the checklist with a stale-source warning.
- Scenario 4 opened blocked Jira and then blocked the task instead of guessing.
- Scenario 5 did not receive source body text and blocked on inaccessible linked docs.
- Scenario 1 noticed the same-file PR but still changed the existing `rotate_token` API; this is a patch-quality gap, not a context-awareness gap.

## Decision

Carry forward `status_only + open-on-demand` as the product architecture, but not as a global instruction to open sources. The next refinement is source-openability: the prompt/context should tell the agent whether source body text is available before it spends a tool call.

## Verification

- `python3 -m compileall -q src tests`: passed.
- `python3 -m pytest`: `54 passed`.
- `python3 -m ruff check .`: all checks passed.
- `python3 -m mypy src tests`: no issues in `20` source files.
- `git diff --check`: passed.
- `gitleaks dir --no-banner --redact .`: no leaks found.
