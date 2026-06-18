Here is the architectural and product review of your context broker design.

### 1. Product or Protocol?
**Steelman for Protocol:** A specification (plus a reference implementation) maximizes ecosystem reach and forces rigorous boundary definitions. If Cursor wants to implement the broker natively in Rust, and an enterprise wants to build a bespoke Java version for their on-prem forge, a strict protocol allows this. Trust is rooted in mathematical/logical guarantees of the spec, not a single vendor’s codebase. 

**Steelman for Product (Packages):** A canonical, executable product guarantees deterministic behavior because you control the extraction logic. Context extraction from Jira/GitHub is messy; relying on third parties to build deterministic connectors guarantees fragmentation. Adoption is driven by friction-free installation (`npm install` or a single binary), not by convincing IDE vendors to read a whitepaper.

**The Commitment:** You must build a **Product (Packages)**. 
For a context broker, the "protocol" is the transport layer (the MCP JSON, the session file format, the coverage certificate). The broker itself is an engine. If you decentralize the engine into a specification, you will suffer immediate semantic drift across implementations, destroying the core value proposition: deterministic, trusted context. You optimize for adoption and impact by providing a canonical, rock-solid binary/package that agents consume via your already-defined hybrid transport. Own the engine; standardize the output.

### 2. Where should the capability boundary live?
You presented a ladder: credential, dependency, process, package. To serve everyone from a solo developer to a regulated enterprise via configuration, the boundary must be a **Package (Dependency) + Process** combination.

*   **Why not just credentials?** Read-only credentials prove you can't write to GitHub, but they do not prove *non-retention*. A paranoid enterprise security team will assume the broker is caching data to disk or phoning home unless proven otherwise.
*   **The Solution:** The base broker must be a standalone, stateless process. The durable memory layer must be a completely separate package (absent from the lockfile/SBOM) that, when installed, runs as a separate process or isolated plugin.
*   **The Enterprise Configuration:** The enterprise audits the SBOM of the base broker. The absence of the memory package mathematically proves the software *lacks the code* to retain state. 
*   **The Solo Configuration:** The solo dev installs the "full suite" wrapper package. The wrapper orchestrates both the broker process and the memory process, wiring them together locally. The boundary remains structurally intact, but the UX is unified.

### 3. Does "durable-as-a-read-source" actually hold?
Structurally, yes. Semantically, it introduces a **temporal re-derivability leak.**

If the memory layer plugs in via the exact same interface as GitHub, the broker technically maintains its pure-function status: given state $S$ at time $T$, it produces output $O$. It cannot track, and the broker itself holds no poisonable state.

**The Leak:** Re-derivability is the victim. When a developer asks, "Why did the agent do this yesterday?", the broker can re-derive the context *only if* it can perfectly reconstruct the state of all sources at that exact timestamp. GitHub and Jira have robust, immutable audit logs and webhooks. If your git-backed memory layer relies on a local, mutating git tree without strict point-in-time querying, the broker will silently pull *today's* memory for *yesterday's* derivation. Furthermore, the memory layer *is* poisonable state (via a bad PR). 

**The Fix:** To maintain the broker's guarantees, the coverage certificate must treat the memory layer with extreme hostility. The certificate must explicitly log the exact immutable commit hash of the memory layer used during extraction. If the memory layer cannot provide an immutable, point-in-time snapshot, it violates the broker's contract and breaks re-derivability.

### 4. Where does the two-package hybrid collapse?
The two-package hybrid collapses into "one product pretending to be two" at the **CLI, Configuration, and Routing layer**.

**The Failure Mode:** The base broker package contains a `--use-memory` flag, or the base broker's configuration file has a reserved `[memory]` block, or the broker's output renderer has hardcoded logic to format "Memory Cards" differently than "Jira Cards." If the base package knows that the memory package exists, the dependency is no longer strictly one-way. The SBOM defense falls apart because the enterprise security reviewer sees memory-layer logic baked into the stateless broker's source code. 

**The Design Rule: Strict Dependency Inversion via Generic Registration.**
The base broker must have absolute zero-knowledge of the memory layer. The broker must only expose a generic `ISource` interface. 
If the memory layer is used, it must inject itself into the broker at runtime as a generic source. The CLI and file renderers must treat memory cards exactly like GitHub cards—relying purely on the typed schema of the context card, not on hardcoded source names. If you delete the memory repository from GitHub, the base broker's codebase shouldn't require a single line of code changed.