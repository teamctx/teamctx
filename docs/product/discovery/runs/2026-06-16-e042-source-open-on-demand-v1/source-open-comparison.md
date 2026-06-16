# Source Open Comparison

Compares E-042 `status_open` against full source access on `primary-02-changed-acceptance-criteria-v1`.

## Aggregate

| Metric | Full source | Status open | Status open delta |
| --- | ---: | ---: | ---: |
| Reported cost | 0.210772 | 0.175604 | -0.035169 (-16.7%) |
| Turns | 8 | 10 | 2 |
| Tool calls | 7 | 9 | 2 |
| Files read | 4 | 3 | -1 |
| Bash commands | 2 | 4 | 2 |

## Quality

| Source access | Quality | Risk noticed | Lookup saved | Changed files | Notes |
| --- | --- | --- | --- | --- | --- |
| Full source | pass 7/7 | yes | yes | `["src/auth/token.py"]` |  |
| Status open | pass 7/7 | yes | yes | `["src/auth/token.py", "tests/test_token_rotation.py"]` |  |

## Behavioral Read

Full source found the Jira acceptance criteria, but also inspected an unrelated GitHub PR snapshot because the whole source tree was present and browsable.

Status open used the intended product path: it ran `python3 .teamctx/open_source.py 'Jira API-482'`, read only the Jira source body, implemented the retry window, added tests, and reported `lookup_saved: yes`.

The cost result favored status open by `0.035169` reported dollars on this one-scenario smoke, while preserving pass-level quality. It did use more turns and Bash commands, which is expected because opening a source is now an explicit action rather than a file read from a pre-exposed source folder.

## Product Implication

Status-only plus open-on-demand is now the best default product shape to carry forward. It lets the agent pull the one source body that matters without turning TeamCtx into a browsable source dump.
