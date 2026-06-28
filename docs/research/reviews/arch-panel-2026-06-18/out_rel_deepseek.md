1 | Open PR #1423 edits the same function `processPayment` in `payment_service.go` that your branch touches | S | Explicit file/symbol overlap edge in the PR graph
2 | Linked ticket PROJ-567 changed to "Blocked" since branch point, must be resolved | S | Linked artifact changed-since-branch state
3 | Required CI check `security-scan` is failing on your branch | S | Dependency edge from branch to required check gate status
4 | Dependency `requests-lib v2.1` pinned in `requirements.txt` has critical CVE-2025-6001 | S | Explicit dependency edge + superseded/affected version from CVE feed
5 | Parent branch `main` is 42 commits ahead of your feature branch, high merge conflict risk | S | Structural measure of branch divergence from merge-base to parent HEAD
6 | CODEOWNERS requires DB team approval for changes in `database/migrations/` | S | Deterministic review gate from CODEOWNERS file (explicit ownership edge)
7 | Service dependency `user-profile-api` has planned maintenance in 2 hours, dev testing will be impacted | S | Service catalog dependency edge + scheduled event on that node
8 | An unlinked design RFC "Decentralized Payment Flow" posted this morning is deeply relevant to your payment refactor | L | No explicit link; requires semantic understanding of topic relevance
9 | Teammate asked in Slack yesterday if anyone knows the legacy billing module you're now modifying | L | Unstructured comms, no link to code artifact; needs fuzzy context matching
10 | Recent merge on `main` introduced a `retryWithBackoff` util that duplicates what you planned to write | L | Semantic code similarity, no pre-existing structural edge
11 | Past co-change history shows touching `convert_currency` in `utils.go` always requires fixing `reporting/tests/` | L | Learned association from usage data, not declared dependency
12 | An incident page about "checkout timeout" appeared today, relevant to your checkout service optimization task | L | Semantic mapping between incident description and work context, no explicit link
13 | Undocumented limit: `FraudDetection` service handles only 100 req/s; your new call might breach it | L | Tribal knowledge never captured in a linked artifact or doc
14 | Personal session note: "remember to profile memory in `data_mapper` before pushing" | L | Personal context from past interaction, no structural trace
15 | Policy: any change to `pricing_engine.py` needs sign-off from legal/compliance team | D | Human-declared custom rule beyond standard ownership edges
16 | Policy: the `experimental` module is frozen until Q3 per leadership decision | D | Durably declared policy (module freeze) not inferable from code or history
17 | Policy: "if I'm working after 9pm, warn me not to push directly to main" (solo dev personal rule) | D | Human-declared behavioral config, stored as durable policy
18 | Architecture decision record `docs/adr/0003-use-grpc.md` was edited since branch, and your branch references it | S | Linked document changed-since-branch state
FRACTION: S=35% L=50% D=15%
BIGGEST_MISS: Tribal knowledge and semantic co-relevance across artifacts (e.g., unlinked RFCs, historical co-change patterns, informal team discussions), because they lack explicit structural edges and cannot be captured by a deterministic graph traversal.