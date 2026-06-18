**Context events for an AI coding agent (START of work)**  

| id | one-line description | CLASS | one-line justification |
|----|----------------------|-------|------------------------|
| 1 | Unmerged PR that touches `src/payment/processor.rs` while the new branch also modifies the same file | S | Structural edge: file overlap with an open PR flags a conflict. |
| 2 | Ticket #1234 (feature flag rollout) marked “blocked” because its linked design doc was updated after the branch point | S | Structural: linked ticket state changed since branch creation. |
| 3 | CI pipeline “security‑scan” marked **required** but not yet passed for the target branch | S | Structural: missing required check gate. |
| 4 | Dependency `lodash@4.17.20` is superseded by a newer vetted version `4.17.21` in the monorepo lockfile | S | Structural: superseded version edge. |
| 5 | Module `analytics` has a declared policy “no changes without data‑privacy review” (config file `.policy.yaml`) | D | Declared: policy enforced by human‑written config, not inferable from graph edges. |
| 6 | The `payments/` package is frozen for Q3 per the team’s release calendar (stored in `release_policy.json`) | D | Declared: temporal freeze declared by management, not captured structurally. |
| 7 | Historical data shows files `ui/button.tsx` and `ui/theme.css` are almost always edited together, though no tickets link them | L | Learned: usage pattern discovered from past co‑change frequency, not an explicit edge. |
| 8 | A recent internal RFC (unlinked) proposes deprecating `legacyAuth` API; the branch will likely need to adapt it | L | Learned: semantic relevance from unlinked RFC, requiring fuzzy matching. |
| 9 | The developer’s personal convention: all new services must include a `metrics` exporter, though not documented anywhere | L | Learned: tribal knowledge inferred from past commits, absent from explicit artifacts. |
| 10 | The branch’s base commit is older than the `schema.sql` migration that added a new column, but the migration file is not listed as a dependency | S | Structural: changed‑since‑branch detection of a migration file (edge exists via file change). |
| 11 | The team’s “no‑direct‑DB‑alteration” policy is declared in `team_policy.yml`; any change to `db/*.sql` must trigger a migration review | D | Declared: policy enforced by config, not discoverable via graph edges alone. |
| 12 | A recent performance regression ticket (`#5678`) mentions “slow JSON parsing” but is not linked to the current module; the module contains a custom parser | L | Learned: semantic link from regression description to code, requiring fuzzy relevance. |
| 13 | The branch modifies `src/config/feature_flags.yml` while the enterprise feature‑flag service requires a rollout approval recorded in `approval_tracker.csv` | S | Structural: explicit edge via linked approval artifact. |
| 14 | The codebase’s style guide (stored in `STYLE.md`) mandates that all public functions have docstrings; the developer often forgets this in new modules | L | Learned: implicit style adherence not enforced by tooling, but inferred from past feedback loops. |
| 15 | The repository has a `CODEOWNERS` entry that assigns `@security-team` as owners of `src/security/*`; any change there must be reviewed by them | D | Declared: ownership policy defined in a config file, not a structural edge. |
| 16 | The branch’s diff includes changes to `src/utils/helpers.js` which, in past releases, always required an update to `src/tests/helpers.test.js` (co‑change pattern) | L | Learned: historical co‑change pattern not captured by explicit links. |
| 17 | A corporate compliance rule (recorded in `compliance_rules.yaml`) states that any modification to GDPR‑related data structures must pass a data‑privacy audit | D | Declared: compliance rule only expressed in policy file. |
| 18 | The branch is based on a commit that predates the removal of a deprecated `crypto` library; the build script still references it, but no explicit dependency edge exists | S | Structural: changed‑since‑branch detection of a removed dependency file. |

---

**FRACTION:** your honest estimate of the share of real‑world HIGH‑VALUE work‑start context events in each class, as S=45% L=35% D=20% (sum 100).  

**BIGGEST_MISS:** the inability of a structural‑only broker to surface *semantic, unlinked knowledge* such as “files that habitually change together” or “tribal conventions”—i.e., the learned/co‑change patterns that drive most surprising breakages.