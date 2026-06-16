# Source Openability Smoke Comparison

Compares E-044 source-openability prompt refinement against the same E-043 `status_open` scenarios.

| Scenario | E-043 cost | E-044 cost | Delta | E-043 quality | E-044 quality | Read |
| --- | ---: | ---: | ---: | --- | --- | --- |
| `primary-01-overlapping-file-change-v1` | 0.075760 | 0.074399 | -0.001360 | review 7/8 | review 7/8 | API preservation improved from `no` to `yes`; remaining review is no validation attempt. |
| `primary-02-changed-acceptance-criteria-v1` | 0.212760 | 0.154788 | -0.057972 | pass 7/7 | pass 7/7 | Body-available path still opened Jira, added tests, and passed. |

## Product Read

Source-openability language appears directionally useful. The collision scenario no longer changed the existing `rotate_token` API after the prompt explicitly said the PR body was unavailable and told the agent to preserve APIs or leave a review note. The Jira scenario still opened the available source body and passed.

This is only a two-scenario smoke. The next proof should rerun the full six-primary `status_open` set with source-openability enabled, or at least the three warning scenarios plus the collision scenario.
