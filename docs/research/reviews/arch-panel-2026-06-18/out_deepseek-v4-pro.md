The right framing is that you’re separating two *architectural roles* — a stateless context function and a durable team memory — that must never be collapsed into a single trust domain. The two-package approach is sound, but only if the seam is enforced at every layer, from dependency graph to runtime isolation. Here’s the concrete position on each question.

---

### 1. Product or protocol? **Specification + reference implementation, where the two-package product is the reference implementation.**

**Steelman for a product-only artifact:** A single, tightly-coupled set of packages (broker + optional memory) gives adopters a turnkey solution with no fragmentation. Consistency is guaranteed; the cross-agent file/CLI surface is the product’s moat, and any third-party reimplementation risks subtle semantic drift that breaks deterministic guarantees. For an open-source tool aiming to be acquired, a polished, opinionated product accelerates initial adoption.

**Steelman for a specification-first artifact:** The true moat is the *protocol* — the context card schema, coverage certificate semantics, and the file/CLI/MCP transport contracts. A specification allows multiple implementations (Rust, Python, Wasm), enables enterprise forks with custom trust models, and avoids vendor lock-in. Trust is maximized when anyone can audit the spec and build a compatible broker, and the memory layer can be implemented independently against the same source interface.

**Commitment: specification + reference implementation serves adoption, trust, and impact better.** The broker’s value is its deterministic, cross-agent contract. That contract *is* a protocol, whether you call it one or not. Publishing it as an explicit, versioned specification (with the current codebase as the reference implementation) invites ecosystem contribution, allows security teams to verify behavior without reading a single codebase, and makes the “no tracking” guarantee auditable at the spec level. The two-package product becomes the canonical open-source implementation, not the only possible one. This is how you earn trust at scale — and adoption follows trust.

---

### 2. Capability boundary: **Package boundary as the primary seam, with process isolation as a configurable hardening layer.**

The ladder of enforcement layers should be stacked as *configurations of the same artifact*, not separate editions:

- **Credential scoping** is table stakes: every source connector (including memory) gets read-only, least-privilege credentials. This is the first line of defense but insufficient alone, because a malicious or buggy memory package could still exfiltrate data it reads.
- **Dependency absence** (memory package not in lockfile/SBOM) is the strongest *declarative* boundary. A regulated enterprise can prove the memory layer is not installed simply by inspecting the dependency graph. This is the seam that makes the separation auditable.
- **Package boundary** (memory as a separate, optional package) is what makes dependency absence possible. The base broker package must have zero imports from the memory package; the memory package depends on the broker’s public source interface.
- **Process isolation** is the runtime enforcement when the memory layer *is* installed. Run the memory layer as a separate process with its own credentials and no access to the broker’s working memory. The broker communicates with it only through the read-source interface (e.g., a local socket or stdin/stdout). This limits blast radius and prevents the memory layer from poisoning the broker’s stateless execution.

**Configuration spectrum:**
- **Solo developer:** install both packages, run them in the same process group for convenience; no process isolation needed.
- **Team with compliance needs:** install both, but run memory as a separate process with read-only access to its git store, auditable via its own logs.
- **Regulated enterprise that forbids durable state:** install only the base broker; SBOM shows memory package absent. This is a configuration, not a separate SKU.

The key is that the broker itself is always stateless and never depends on the memory layer. The memory layer’s presence is a deployment choice, enforced by the package manager and optionally hardened by process boundaries.

---

### 3. “Durable-as-a-read-source” holds — but the trust boundary shifts, and that shift must be explicit.

The broker’s structural guarantees are:
- **Can’t track:** no retained request logs, no behavioral state.
- **No poisonable accumulated state:** output is a pure function of current source state; no hidden memory that an attacker could corrupt across sessions.
- **Full re-derivability:** given the same source states at time T, the output is identical.

When the memory layer is plugged in as a read source, the broker treats it exactly like GitHub or Jira: it queries the source at invocation time, extracts features, and produces cards. The broker itself retains nothing. The memory layer retains state, but that state is *external* to the broker, just as a Jira ticket’s history is external. The broker’s coverage certificate will honestly report whether the memory source was consulted and whether its data was stale or unknown.

**No leak of the broker’s guarantees.** However, the *system’s* trust model now includes the integrity of the memory source. A poisoned memory entry (e.g., a malicious PR that merges false “decisions”) will cause the broker to serve misleading cards. That’s a source-integrity problem, not a broker-design problem. The human PR-review gate mitigates this, but it’s a people/process control, not an architectural guarantee. The broker remains stateless and re-derivable; the memory layer is the stateful component with its own threat model. This separation is clean as long as the broker never caches or interprets memory data beyond the current query.

**One subtlety:** if the memory layer’s state grows unboundedly and the broker’s query interface doesn’t paginate or limit, a huge memory store could cause latency or resource exhaustion. That’s an operational concern, not a structural leak, but it should be addressed in the source interface contract (e.g., timeouts, size limits).

---

### 4. The collapse mode: **When the memory layer becomes de facto required for core value.**

The specific failure mode is that the broker’s headline promises — “every agent starts knowing what the team decided” or “no agent misses a handoff” — become impossible without the memory layer. Then the “optional” package is a fiction; users must install it to get the advertised benefit, and the separation is just a config toggle pretending to be an architectural boundary.

**Design rule to prevent collapse:**
1. **The broker’s core value proposition must be fully realized with zero dependency on the memory layer.** The stateless broker alone must deliver compelling, cross-agent context from live sources (PR overlaps, stale acceptance criteria, superseded docs). The memory layer adds *durable team knowledge* on top, but that is an additive feature, not the core.
2. **The broker’s public API and documentation must never mention the memory layer as a required component.** The memory layer is a plugin that implements a source interface; the broker’s specification must be written such that a third-party could build an entirely different durable store (or none) and still be a conformant broker.
3. **Separate distribution and versioning.** The memory package must be installable independently, with its own release cadence. It must not be bundled in the broker’s default installation (e.g., `pip install context-broker` does not pull in memory; `pip install context-broker[memory]` does).
4. **Test the broker in isolation.** The CI suite must run the full broker test suite with the memory source connector absent, proving that no functionality silently depends on it.

If these rules are followed, the two-package hybrid is genuine. The moment the broker’s README says “for team knowledge, install the memory package” as if it’s a required step, the collapse has begun. The seam is real only if the broker is a complete, useful product without it.