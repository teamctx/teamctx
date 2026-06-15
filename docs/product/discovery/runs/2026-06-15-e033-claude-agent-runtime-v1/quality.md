# Claude Agent Quality Summary

| Fixture | Model | Variant | Level | Score | Risk noticed | API preserved | Notes |
| --- | --- | --- | --- | ---: | --- | --- | --- |
| `primary-01-overlapping-file-change-v1` | `sonnet` | baseline | review | 7/8 | yes | yes | no validation command or test change captured |
| `primary-01-overlapping-file-change-v1` | `sonnet` | context | review | 6/8 | yes | no | no validation command or test change captured; changed existing rotate_token API in collision scenario |
