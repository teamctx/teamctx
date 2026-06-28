# Architecture / Category Review: context broker for AI coding agents

You are on an expert panel reviewing a **product + architecture** decision. Respond
with rigor and a clear point of view. **Evaluate ONLY on product, architecture,
trust, adoption, and impact grounds.** Do NOT comment on fundability, pricing,
go-to-market, business model, or company-building, that feedback is explicitly
unwanted and will be discarded. This is an open-source product (possibly acquired
later); the author optimizes for adoption, trust, technical soundness, and impact.

## Background (sanitized, conceptual)

We are building a **deterministic, non-LLM, read-only "context broker"** for AI
coding agents. At the start of a unit of work (e.g., a session or a new branch),
any connected agent (Claude Code, Codex, Gemini CLI, Cursor, opencode, etc.)
asks the broker for context. The broker returns compact, typed, permission-scoped
**context cards** ("there's an open PR already touching this file"; "the linked
acceptance criteria changed after your branch point"; "this doc was superseded")
plus a **coverage certificate** that honestly reports which sources were observed,
which are stale, and which are unknown (absence of a card never implies "all
clear"). Sources are first-class connectors: GitHub, GitLab, Jira, Confluence.

Key properties already established (a formal protocol paper backs these):
- **Deterministic / no LLM** in the core: same inputs produce same outputs;
  selection is by typed feature extraction, not a model, which makes it
  injection-resistant and replayable/auditable.
- **Read-only**: no write path to sources.
- **Privacy by architecture**: artifact-centric, no people-graph, no read
  receipts, no behavioral tracking.
- **Cross-agent** via a hybrid transport: a context **file** (written at session
  start, any client can read it), a **CLI**, and an **MCP** server. The
  file/CLI path is the cross-agent moat, it needs no per-client plugin.
- Transport surfaces are deterministic *renderers* of the same certified cards
  (file, CLI, IDE panel, MCP JSON), never an in-editor LLM assistant.

## The decision under review: the stateless/durable seam

There is an optional **durable memory layer** (call it the "memory layer"): a
git-backed, reviewed-write store of durable team knowledge (decisions, principles,
handoffs) with a human PR-review gate. This is the lineage's original design, the
broker and the memory layer were once a single unified tool.

We have come to believe the natural seam between them is **statelessness vs.
durability** (NOT read vs. write):
- The **broker is stateless**: its output is a pure function of *current* source
  state. It retains nothing, so it structurally "can't track," has no poisonable
  accumulated state, is fully re-derivable, and has nothing to subpoena.
- The **memory layer is durable**: it accumulates trusted knowledge over time,
  which is its entire value, and also its only poisoning / drift / retention
  liability.

These map to two headline promises that are in direct tension *inside a single
artifact*: "it can't track, it can't" (needs non-retention) vs. "every agent
starts knowing what the team decided" (needs retention).

Current leading proposal: **two tightly-coupled packages, one product.** A base
broker package (stateless, everyone installs it) plus an *optional* durable-memory
package that a security team can decline to install. The capability boundary is
then an **auditable dependency-graph fact** (SBOM shows the memory package absent),
stronger than a config flag. The memory layer would register as *just another read
source* to the broker, so the broker stays stateless even when memory is present;
only the memory package retains state. Strict one-way dependency: the broker is
ignorant of the memory layer; the memory layer depends on the broker's interfaces.

## Your task: answer all four, take a position, don't hedge

1. **Product or protocol?** Is the right artifact one-or-more *packages*, or a
   *specification + reference implementation + third-party implementations*?
   Steelman BOTH, then commit to which serves adoption/trust/impact better and why.
2. **Where should the capability boundary live?** Given a ladder of independent,
   stackable enforcement layers, credential (read-only scope) / dependency
   (package absent from lockfile) / process (separate process, read-only creds) /
   package (code not on disk), what combination correctly serves the range from
   solo developer to regulated enterprise *as configurations, not editions*?
3. **Does "durable-as-a-read-source" actually hold?** If the durable memory layer
   plugs into the broker through the same interface as GitHub/Jira, does the broker
   genuinely keep its structural guarantees (can't-track, no poisonable state, full
   re-derivability), or does one of them quietly leak? Be concrete about the leak
   if there is one.
4. **Where does the two-package hybrid collapse** back into "one product
   pretending to be two"? Name the specific failure mode and the design rule that
   prevents it.

Be concrete and opinionated. If you think the framing itself is wrong, say so and
reframe. ~600–900 words.
