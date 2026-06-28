# Slice C-judge: rebuild why/open-source on the live broker

**Status:** designed, DEFERRED for CPO nod on the selector UX before building. **Date:** 2026-06-28.
Codex (gpt5.5 xhigh) consulted; recommended Option B; I (CTO) agree.

## Why this one is deferred rather than driven solo
It is the one remaining slice that combines three things: it is all-or-nothing (the core plumbing has
no user value without the commands, so it cannot be half-shipped), it touches the sensitive core (the
broker answer must start carrying open-targets), and the selector UX is a genuine product call. That
mix is worth a 30-second CPO nod before I touch the core for it. Everything else this session I drove
to merge.

## Decision (Codex B + arbitration)
**Keep why/open-source; do not retire them.** The inline M2 render gives the basics (what changed plus
a `gh pr view N` hint), but the standalone commands add real value: the full audit evidence (the
deterministic rule, the reason code, freshness, confidence, source-body policy) and a policy-gated
source-opener, and they cover issues, docs, gates, and future providers that the inline hint does not.
**No opaque handles** (they are either unstable output-order IDs or just natural selectors with extra
ceremony). Use **typed natural selectors** that are already visible in the prose.

## Command shape (the part wanting a nod)
```
teamctx why pr:7 --path src/app.py
teamctx open-source pr:7 --path src/app.py
```
Selectors: `pr:N`, `issue:#N`, `path:<path>`, `doc:<path>`, `gate:<name>`. Both commands take the SAME
resolution options as `work-start` (repo, branch, token-env, issue, since, docs-root, ref,
include-title). They rerun the live broker, match exactly ONE current finding, and fail honestly if
none or many match (rerunning means the answer can differ from an earlier `work-start` if the source
changed since; that is the right trade for a live, snapshot-free, source-of-record-aligned tool).

`why` renders: finding text; why this matters; the deterministic rule and reason code; source display;
the allowed evidence from the signal scope (changed path / issue / gate / doc / URL); freshness,
confidence, checked time; source-body policy.

`open-source` renders: source label; the concrete opener (`gh pr view 7 --repo org/repo`, an issue
URL, a doc path, or a check URL); body availability; and the policy reason when the body is
status-only or unavailable.

## Plumbing required (the core touch, additive and verdict-neutral)
- `BrokerAnswer` carries `selection` + `verdicts` today and DROPS the composed `open_targets`. Add
  `open_targets: tuple[SourceOpenTarget, ...]` to `BrokerAnswer`; thread it through `broker_answer`
  (additive keyword, default `()`) and have `broker_answer_from_documents` pass `composed.open_targets`.
  The verdict derivation is untouched, so the purity test and the theorems are unaffected.
- Confirm the selection's cards link to their open-target via `card.source_open_target_id`.
  `forge_review` sets it on its cards; verify `select_context` carries it onto the derived selection
  cards, and add the linkage if not (Codex flagged that live cards may currently have
  `source_open_target_id=None`).
- Matching: a selector resolves to the one finding card whose scope/source matches (`pr:N` -> the
  collision card for PR N; `path:X` -> the card touching X; etc.). Exactly-one-match or an honest,
  decision-enabling failure message.

## Build plan (when greenlit)
One cohesive slice: the plumbing + selector parsing + matching + the two renderers + the two commands
+ tests. Codex review (core-touching). Surfaced-text bar on all output; zero em dashes.

## The nod I need from Edgar
1. Selector syntax `pr:7` / `path:src/app.py` / `issue:#42` / `doc:` / `gate:`: good, or different?
2. Confirm keeping why/open-source at all (Codex and I say keep for the audit/open affordance; the
   inline render covers the basics). If you would rather they stay retired, that is a one-line answer
   and saves the slice.
