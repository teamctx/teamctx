# Ambara harvest: what to reference for teamctx

**Date:** 2026-06-29 · **Status:** reference notes (not a build plan)

Ambara (`agents/repos/ambara`, beta v0.7.0) is teamctx's lineage predecessor and our deferred
durable-memory layer. This is a CTO read of what is worth **referencing** as we build teamctx's
planned pieces. The discipline is reference only: we design and build new and clean here. Ambara's
code is not ported; its ideas and contract shapes inform ours.

## Framing: where it overlaps, where it diverges

Ambara and teamctx overlap on one layer and diverge on the product.

- **Overlap (the reusable part):** source ingestion. Both pull forge / work-tracker / docs artifacts
  under a policy, trust, and provenance model. Ambara is more mature here. It has a frozen
  source-artifact contract, a conformance kit, an auth-broker seam, a typed omissions concept, and
  text-trust marking. These are problems teamctx hits in Sprint 4 and the going-public security pass.
- **Diverge (keep separate):** the product. Ambara is durable memory for agents ("agents forget;
  save where I left off"). teamctx is reality-grounding before you act. Agent-memory is the category
  we deliberately differentiate from, so none of that framing or scope should leak into teamctx.

## Tier 1: relevant now (sharpens what we just built or are exposed on)

### 1. `SourceOmissions`: typed, reason-categorized "what I did not see, and why"
Ambara (`sources/types.py`) carries omissions as a frozen, composable count by reason:
`privacy`, `safety`, `budget`, `freshness`, `source_error`, with `.total` and `+`. The `budget`
category is exactly the page-limit truncation we just fixed in the PR and gate connectors with ad-hoc
`coverage_truncated` booleans; `freshness` and `source_error` are the other honest-UNKNOWN causes.

- **Why reference it:** we carry incompleteness as one-off flags today. One typed omissions concept
  threaded connector -> coverage -> render is the principled version, and it is precisely what the
  deferred `incomplete[unbounded]` precise-truncation work needs.
- **How to use it:** design teamctx's own minimal version (probably `truncated / unreachable /
  policy-excluded`), feed it into `core/select.py` `assess_completeness` so the render can say exactly
  what was incomplete and why. Reference the shape and the reason-categorization, not the code.

### 2. `TextTrust` + `SourceSafetyVerdict`: untrusted-external text marking
Ambara tags every artifact's text with a trust level (`trusted_internal`, `untrusted_external`,
`blocked_external`, `summary_generated`) and a per-artifact safety verdict.

- **Why reference it:** teamctx surfaces external text to agents (PR titles via `--include-title`
  today, more later) with no trust marker. That is a prompt-injection surface: a malicious PR title
  can reach an agent as if it were content. Our no-LLM-in-the-content-path thesis makes this worse,
  not better, because we hand text through verbatim.
- **How to use it:** a minimal text-trust marker on any external text we surface, so the render and
  the MCP output flag untrusted-external content. This is a security hardening to do before going
  public or feeding autonomous agents. Reference the concept; build ours small.

## Tier 2: reference for Sprint 4 (more source families)

### 3. Frozen source-artifact contract + conformance kit (ADR 0001)
Ambara freezes one source-agnostic `SourceArtifact` that all families implement against, pinned by a
guard test and changeable only via a superseding ADR, plus a no-network conformance kit
(`sources/conformance.py`, `check_source_provider_contract` -> findings) that a provider must pass to
be supported. Capability growth happens via `SourceCapabilities` flags, not by reshaping artifacts.

- **Why reference it:** the README promises "a source becomes supported only after it proves the same
  honest-coverage behavior," and we have no harness for that. This is how to make it real and de-risk
  Jira/GitLab.
- **How to use it:** when the second source family lands, decide whether our `SourceSignal` contract
  scales or needs a freeze, then build a conformance harness. Reference the capability-flags idea and
  the conformance-findings model.

### 4. Auth-broker seam (ADR 0002)
`SourceAuthRef` names auth by reference (`env` / `keyring` / `managed`, never raw); a broker resolves
it at runtime; raw credentials never enter config, artifacts, cache, or output. Our
`resolve_token(token_env)` is the env-only special case of exactly this.

- **How to use it:** when a second auth-requiring source lands, generalize `resolve_token` into that
  seam (resolve by reference, never raw). Adopt the never-persist-raw-credentials invariant explicitly
  now; we are already aligned since we resolve by env or file name.

## Tier 3: reference for the deferred memory layer (not now)

### 5. `plan_remember` promote decision (ADR 0003)
One pure, deterministic decision for "should this become durable memory, at what trust level,"
running a content-policy gate, escalation, contradiction detection, an honest receipt, and a
provenance footer. Promote opens a review branch and never re-reviews ("a PR already exists where the
decision was made; remembering does not re-review").

- **Why reference it:** this is the honest-memory invariant our deferred layer needs. A remembered
  fact is provenance-linked and advisory-until-promoted, never a re-adjudication and never
  stale-masquerading-as-fresh.
- **How to use it:** when we build memory, reference the advisory->promoted gate and
  contradiction-on-write. The trusted path must still re-check; a remembered "clear" stays stale
  until verified. This is the same surface-don't-adjudicate stance teamctx already holds, applied to
  memory.

## Skip (do not inherit)

- The MCP-server plumbing (`server_*.py`). Ambara is heavily server-shaped; we have our own broker and
  transports. Harvest the `core` / `sources` models, not the wiring.
- The agent-memory product framing. It is the category we differentiate from.
- `BodyPolicy`'s excerpt/summary body-fetching. It would erode our metadata-only stance.

## Recommendation

Two items are relevant now and small: the **omissions concept** (sharpens honest-UNKNOWN and completes
the truncation work) and the **untrusted-external text marker** (a pre-public injection hardening). The
rest are genuine Sprint-4 and memory-layer references to revisit when we get there. Build everything
new and clean in teamctx; Ambara is reference, not a parts bin.
