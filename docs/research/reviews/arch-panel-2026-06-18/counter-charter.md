You are a skeptical principal engineer. A 4-model panel reached a consensus on the
architecture of a deterministic, read-only, cross-agent "context broker" for AI
coding agents (returns typed "context cards" + an honest "coverage certificate" of
what was/wasn't observed). Your job is to ATTACK the consensus and find where it is
wrong, naive, or theater. Product/architecture/trust/adoption lens ONLY — never
business model, pricing, or GTM.

THE CONSENSUS YOU MUST ATTACK:

1. Ship it as a "specification + reference implementation," not just packages —
   publish a Context-Broker Protocol (card schema, coverage-certificate semantics,
   source-connector interface, determinism rules); the codebase is the reference
   impl; third parties can build compatible brokers. (One panelist dissented: said
   own the ENGINE as a canonical product, only standardize the OUTPUT/transport,
   because decentralizing the engine causes semantic drift that destroys the
   deterministic guarantee.)

2. The stateless broker and the optional durable "memory layer" should be TWO
   packages, one product. Capability-absence is proven by the DEPENDENCY GRAPH /
   SBOM (memory package absent from the lockfile = provably can't retain), hardened
   by process isolation and read-only credentials. A solo dev installs both; a
   regulated enterprise installs only the broker and audits the SBOM. Configurations,
   not editions.

3. "Durable-as-a-read-source" holds: the memory layer plugs into the broker via the
   same interface as GitHub/Jira, so the broker stays stateless even when memory is
   present — PROVIDED the memory layer is a pure read source (no query-driven
   mutation, no write-back on read, no broker-side caching across calls), and the
   coverage certificate pins the memory layer's immutable commit hash.

4. The hybrid stays honest only if the broker is fully useful WITHOUT memory, has
   ZERO knowledge of the memory layer (generic source interface, runtime
   registration, no hardcoded memory logic / no `--use-memory` flag), and CI proves
   the broker passes with memory absent.

ATTACK IT. Specifically:
- Is "protocol + reference implementation" a trap? Does it actually dilute the
  deterministic/trust guarantee or slow adoption vs. just shipping a great product?
- Is SBOM/dependency-absence capability-proof meaningful to a REAL security
  reviewer, or is it theater that a determined adversary or a careless ops team
  defeats anyway?
- Where will "durable-as-a-read-source" leak in PRACTICE (not theory)?
- What did all four models MISS entirely? Name the biggest blind spot.

Be concrete, contrarian, and brief (~400-600 words). If the consensus is mostly
right, say which ONE part is most fragile and why.
