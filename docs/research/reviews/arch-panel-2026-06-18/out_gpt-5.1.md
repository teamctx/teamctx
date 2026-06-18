1. **Product or protocol?**

You’re sitting on something that *wants* to be a protocol with a canonical implementation, not just a library:

- The core value is:  
  - deterministic selection semantics,  
  - typed context cards,  
  - explicit coverage certificates,  
  - and transport-agnostic rendering.  
  That’s a *contract* more than a “library feature set.”

- Trust arguments (“can’t track”, “no poisonable accumulated state”, “coverage certificate is honest”) are *only* really defensible if:  
  - multiple independent parties can implement / verify, and  
  - the protocol is sufficiently crisp that “compliant vs. non-compliant” is a meaningful statement.

Steelman both:

**A. Product-first (packages only)**  
Pros:
- Fastest path to adoption: one CLI + daemon developers can just install.
- You can enforce your exact semantics and threat model without spec drift.
- Lower cognitive load: “install broker; optional: install memory” is concrete.

Cons:
- All trust arguments hinge on *you* being honest and careful — “protocol paper” helps but is still de facto “trust the vendor.”
- Ecosystem lock-in: agents integrate to *your* CLI/MCP server, not a widely accepted spec.
- Regulated buyers will eventually ask: “What *exactly* is this thing doing? Is there a standard?”

**B. Protocol + reference implementation**  
Pros:
- Stronger trust: a published, testable spec for:
  - card schemas and types,
  - source connector interface,
  - coverage certificate semantics,
  - determinism guarantees (e.g., no time-based randomness, no cross-session state).
- Ecosystem leverage: agent vendors and IDEs can ship their own implementations but still be “context-broker compatible.”
- Makes the stateless/durable seam inspectable: the durable memory layer must speak the same read-source protocol; reviewers can see whether it actually preserves the stateless guarantees on the broker side.

Cons:
- More up-front design work and maintenance (conformance tests, versioning, etc.).
- Risk of low-quality third-party implementations hurting perceived reliability if the spec is underspecified.

**Position: protocol-first with a strong canonical product.**

You should define:

- A **Context Broker Protocol (CBP)**:
  - message format for “context cards”
  - required metadata (source id, version/commit, timestamp, permissions)
  - “coverage certificate” schema and semantics
  - determinism / replay rules
  - connector interface (what a “read source” must expose)

- A **reference broker implementation** (what you’re building):
  - CLI + file writer + MCP server are just transports around that protocol.
  - Open-source, test harnesses to verify determinism / coverage behavior.

- The **durable memory layer** as a protocol-compliant source implementation.

This maximizes adoption and trust without sacrificing the concrete “one thing to install” story. The product is: “the reference broker + official connectors,” but the architecture is: “this is a protocol; our implementation is one well-audited instance.”

---

2. **Where should the capability boundary live?**

You described four levers:

1. Credential: read-only scopes / which sources are even accessible.
2. Dependency: memory package present/absent in the lockfile / SBOM.
3. Process: separate process with its own credentials.
4. Package: code not present on disk / not in the container image.

You want configurations, not “editions,” that scale from solo to regulated enterprise.

My proposed *normative baseline* (the “secure-by-default, extend-by-explicit-choice” design):

- **Broker binary/process must be structurally stateless:**
  - No persistent storage beyond ephemeral caches (in-memory or temp files that don’t survive process restart).
  - No dependency on any package that performs durable writes.
  - This is enforced via:
    - **Dependency boundary**: broker package has no dependency (direct or transitive) on memory-layer packages.
    - **Process boundary**: any durable store must be in a separate process; the broker interacts with it only via the read-source protocol over a well-defined IPC/HTTP/local socket.

- **Memory layer must run as an *external connector* with its own identity and credentials:**
  - Own process, own config, own git remote.
  - Broker sees it exactly like “GitHub” or “Confluence” — a read-only source authenticated with a separate token or socket.
  - This gives you a **credential boundary**: disabling memory is as simple as not configuring the connector (or providing no credentials).

- **Package/code boundary for high-assurance environments:**
  - For regulated enterprise, the decisive guarantee is: “this deployment artifact literally contains no durable memory code.”
  - That’s the **package boundary** and **dependency boundary** combined: a “broker-only” container/image with:
    - no disk path for durable storage,
    - no memory-layer binaries or libraries,
    - SBOM proving absence.

Concretely:

- **Solo dev / team with low regulatory constraints:**
  - Single container or local install containing:
    - broker binary
    - optional memory-layer binary
  - Still **separate processes**, but same host.
  - Turning off memory: don’t run the memory process; don’t configure that source.

- **Security-conscious / enterprise:**
  - Two possible patterns:
    - (a) Broker-only container image (SBOM shows no memory layer) — no way to accidentally bring memory in.
    - (b) Broker container + memory-layer container, separately managed, connected via network/IPC with read-only protocol from broker’s perspective.
  - Memory layer deployed only where allowed; some orgs may never deploy it.

Key: *do not* rely purely on config flags inside a single binary. For trust and audit, you want:

- For “no durable state” promise:
  - **No code present** that can write durable state.
  - **No filesystem path** configured in the broker to write persistent data.
- For “durable memory optionality”:
  - Memory is an external source that can be entirely absent at:
    - dependency graph,
    - deployment artifact,
    - runtime configuration.

---

3. **Does “durable-as-a-read-source” actually hold?**

If done strictly, yes — but there are two important potential leaks.

**Correctly done:**

- The broker’s observable behavior at time T is a pure function of:
  - current state of external sources (GitHub, Jira, memory, etc.),
  - the explicit query parameters (branch, repo, user-supplied path, etc.),
  - *no* historic internal state.

Under that condition:

- “Can’t track”:  
  The broker itself does not persist anything. Knowledge about previous queries can only exist in:
  - external sources (e.g., Github logs),
  - transport logs (CLI history, MCP logs),
  but not inside broker or memory-layer *because of the broker*.

- “No poisonable accumulated state” (within the broker):  
  It does not learn long-lived, mutable “beliefs.” If a durable source is poisoned, it’s just like a poisoned Git repo or Confluence page — an external input, not internal accumulation. You can rollback or snapshot those sources and deterministically re-derive broker output.

- “Full re-derivability”:  
  Given:
  - the exact versions / commits of each source at time T, and
  - the same broker version and config,  
  you can recompute outputs. The memory layer being durable doesn’t change that; it’s just another versioned input.

**Where the seam can leak:**

1. **If the broker differentiates between “normal” sources and the durable layer in its selection logic.**  
   Example leak: “Always prefer durable memory cards over any other source when conflicts arise.”  
   If that preference is *not* specified as a generic policy (e.g., sources have priority weights, and memory is just one with a configured weight), auditors will treat this as a “secret special relationship.” The antidote: memory looks exactly like any other source at the protocol level; any prioritization or merging logic is source-agnostic.

2. **If the durable layer can infer query patterns and then change future responses.**  
   You must prevent the memory layer from using query history to serve different content *about the same logical state*. For example:
   - Memory layer stores: “This team has asked about `foo.py` 50 times; mark this as ‘hot’ and add a new card.”  
   That would mean the output at time T+1 depends not just on source state but also on the query history. From the broker’s perspective, that’s still “source state,” but substantively you’ve reintroduced tracking *in the memory layer*.

   To preserve the broker’s **structural guarantees**, you need a design rule for the memory layer:

   > The durable memory store must only change its observable state via explicit, human-reviewed writes (PRs, merges), not via autonomic, query-driven updates.

   If that holds, the broker’s guarantees remain intact: any change in cards is attributable to explicit content changes, not “who asked what when.”

So: “durable-as-a-read-source” holds *if and only if* the memory layer is forbidden at the protocol level from mutating in response to broker queries.

---

4. **Where does the two-package hybrid collapse back into “one product pretending to be two”?**

The collapse happens when the stateless/durable split is only *logical* or *configural*, not structural. Two concrete failure modes:

1. **Shared binary / shared code paths that can flip via config.**  
   E.g., a single `broker` binary that:
   - has compiled-in durable memory code,
   - can be turned “off” with a config flag like `enable_memory=false`.

   Failure:  
   - From an auditor’s POV, the capability exists inside the same artifact; “off by config” is weak assurance.
   - A bug or misconfig can silently turn it on.
   - “It can’t track — it can’t” becomes “it can track, but you asked us nicely not to.”

   **Design rule:**  
   - The broker artifact (binary/container/package) **MUST NOT** contain any code paths that can perform durable writes or track query history.
   - Presence/absence is enforced at build and packaging time, verified by SBOM.
   - Any durable-capable component must be a separate binary/package, separately versioned and deployable.

2. **Implicit coupling in UX and default flows.**  
   Example:
   - You ship a “broker install” script that:
     - by default installs memory layer,
     - auto-configures the broker to connect to it,
     - frontends both as if they’re a single cohesive product.
   - IDE integrations talk to “the broker” but silently rely on memory being there for key experiences.

   Failure:
   - In practice, users and orgs cannot meaningfully separate them; turning one off degrades core functionality.
   - Over time, features, docs, and assumptions entangle until treating them as separate modules is a legal fiction.

   **Design rule:**
   - The broker must be *functionally complete* and useful without the memory layer.
   - Documentation and UX must treat “memory source” as an *add-on connector*, not a core layer.
   - First-run path: broker comes up with only stateless sources; adding memory is an explicit, well-documented step (and ideally, involves a human review step consistent with the “PR gate” ethos).

If you enforce:

- separate binaries/processes,
- independent packages and SBOMs,
- a protocol that treats memory as a plain read source,
- and a hard rule that the broker bundle contains no durable code,

then “two tightly-coupled packages, one product” remains honest: one product experience, but with a clean architectural seam where trust and retention guarantees differ and are independently auditable.