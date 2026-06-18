# Experiment: undeclared cross-artifact disagreement detection (2026-06-18)

**Question.** Can a deterministic extractor + phantom filter detect *real*
cross-artifact disagreements precisely enough to ship as a CERTIFIED card, or must
undeclared disagreement stay an untrusted (L) hint?

**Method.** 3 frontier models (gpt-5.1, deepseek-v4-pro, gpt-oss-120b) each generated
16 adversarial, ground-truth-labeled artifact pairs (48 total) — messy realistic
ticket/doc text with traps: superseded sections that still contain the old value,
"was X now Y", representation ("5" vs "5 attempts" vs "1 initial + 4 retries"), unit
equivalence, scope-mismatch, freetext. Two reasonable deterministic detectors
(general rules, not tuned to the corpus) were run once each.

**Result (positive class = "disagree"):**

| detector | scope | precision | recall |
|---|---|---|---|
| v1 | all | 0.44 | 0.41 |
| v1 | structured | 0.44 | 0.58 |
| v1 | freetext | — | 0.00 |
| v2 (improved) | all | 0.44 | 0.41 |
| v2 | structured | 0.44 | 0.58 |

False positives ("cried wolf") concentrate in **representation** (4) and
**superseded-section** (3) — the structurally-hard cases. Freetext recall = 0
(needs semantics, banned from the core). v2's fixes (count-unit normalization,
arithmetic, superseded stripping) only swapped one error for another: precision
stuck at 0.44.

**Decision.** Undeclared cross-artifact disagreement does NOT clear certify-grade
precision and **stays an L (untrusted hint)**. The broker certifies only:
(a) the *structural* fact that both linked artifacts CHANGED / are relevant
("they may now disagree — check"), needing no value extraction; and
(b) DECLARED-authority comparison on a *typed/structured* field, where the
extraction target is pinned and human-reviewed.

**Caveats.** Corpus is adversarial (worst-case, not production frequency) — but
adversarial is the right bar for "certified = rely without checking," and superseded
sections / "was-now" are common in real docs. The detector is a reasonable
approximation, not a maximal φ; a serious effort could lift *structured* precision,
but freetext is unreachable deterministically and the burden of proof (~0.9 on
adversarial inputs) is steep. Revisit only by beating that bar on this kind of corpus.
