**TL;DR** – The “context‑broker” should be published as a **specification + reference implementation** that can be consumed as a **stand‑alone, stateless package**.  A **second, optional “memory‑layer” package** lives on top of that spec and is the only place where durability is introduced.  The boundary between the two must be enforced by **dependency‑graph (SBOM) + runtime read‑only credentials**, not by a hidden monolith.  When the memory layer is wired in as a regular read‑source the broker’s guarantees still hold, **provided the memory layer is treated as a pure data source** – any deviation (e.g., caching mutable state inside the broker) is the leak.  The hybrid collapses back to “one product” when the memory‑layer code is *merged* into the broker repository or when the broker starts to *write* to that store; the rule that prevents this is **“the broker never holds mutable state across invocations”.**  

Below is the detailed reasoning that leads to that conclusion.

---

## 1. Product vs. Protocol – Steel‑man Both, then Choose

### Steel‑man: Publish as a **set of packages** (single‑product model)

* **What it looks like** – One GitHub repo, two distributable artifacts:  
  *`broker-core`* (pure‑function library, CLI, and MCP server) and  
  *`broker‑memory`* (git‑backed knowledge store, PR‑review workflow).  
* **Adoption arguments** – Simpler for teams that want “just the broker”: they install `broker-core` and get a deterministic, zero‑trust component with no extra dependencies.  The memory layer can be added later with a single `pip install broker‑memory`.  
* **Trust arguments** – The SBOM of a deployment can be inspected; if `broker‑memory` is missing, the system is provably stateless.  Auditors can verify the `broker‑core` binary hash matches the reference implementation.  
* **Impact arguments** – A single repo lowers the barrier for contributors, encourages a shared code‑ownership model, and makes it easy to ship coordinated releases (e.g., a new source‑connector added to both packages at once).

### Steel‑man: Publish as a **specification + reference implementation (RI) + third‑party implementations**

* **What it looks like** – An open specification (e.g., “Context‑Broker Protocol v1”) that defines:  
  * the *request* format (session ID, credential set, optional feature flags)  
  * the *response* format (typed cards, coverage certificate)  
  * the *source‑connector* contract (read‑only, deterministic extraction).  
  The reference implementation lives in a repo, but any vendor can ship a compatible library (Rust, Go, JavaScript, etc.).  
* **Adoption arguments** – Teams can embed the protocol in existing tooling (e.g., a build‑system plugin) without pulling in a heavyweight broker binary.  Language‑specific SDKs can be thin wrappers around the spec, making the broker feel native to the developer’s stack.  
* **Trust arguments** – Because the spec is immutable and versioned, auditors can reason about *any* implementation that claims conformance.  The RI serves as a “golden reference” for conformance testing; a third‑party can be vetted once and then used forever, decoupling security review from release cadence.  
* **Impact arguments** – A spec invites ecosystem growth: IDE vendors, CI providers, and security tooling can all implement the same contract, leading to a de‑facto standard for “AI‑coding context”.  This multiplies the reach beyond the original maintainer’s community.

### Which serves adoption, trust, and impact better?

**The spec‑plus‑RI approach wins.**  

* **Adoption** – Open‑source ecosystems thrive on language‑agnostic standards.  By exposing a clean, versioned protocol, you let existing CI/CD pipelines, IDE extensions, and internal tooling adopt the broker without forcing a particular packaging model.  The “two‑package” idea can still be expressed as two *implementations* of the same spec (a stateless core and an optional durable source) rather than two tightly‑coupled binaries.  
* **Trust** – Determinism and read‑only guarantees become *protocol properties* rather than “implementation quirks”.  Auditors can verify a deployment by checking that every component that claims to be a “source connector” adheres to the deterministic extraction contract.  The reference implementation is still valuable for boot‑strapping, but the spec is the ultimate trust anchor.  
* **Impact** – A spec encourages third‑party ecosystems (e.g., a vendor‑supplied Confluence connector, a corporate‑internal “policy‑store” source).  The more independent implementations, the more the broker becomes a platform rather than a product, increasing the probability of long‑term sustainability and community‑driven extensions.

**Therefore:** Publish a **formal protocol** (v1) with a **reference implementation** that ships as a **stateless core package**.  The durable memory layer is **another source connector** that implements the same protocol; it is distributed as a separate package that *depends* on the core but never vice‑versa.

---

## 2. Where the Capability Boundary Should Live

The boundary must be enforceable **both at build‑time and run‑time**, and it must scale from a solo developer (who may just drop a single binary on the path) to a regulated enterprise (which needs auditable guarantees).  The following layered enforcement works:

| Layer | Mechanism | What it protects | Typical configuration |
|------|-----------|------------------|-----------------------|
| **Credential** | Read‑only OAuth / Git‑access token scoped to *only* the source connectors (GitHub, Jira, memory‑store). | Guarantees the broker cannot write to any source, even if a malicious connector is added. | `BROKER_READ_TOKEN` env var; CI secrets manager. |
| **Dependency** | **SBOM / lock‑file** entry – presence of `broker‑memory` package. Absence → broker runs in “pure‑stateless” mode. | Guarantees that no durable state is reachable without explicit inclusion. | `package.json` / `requirements.txt` – tooling can enforce “no‑memory” policy. |
| **Process** | Run the broker core in a sandboxed process that only loads connectors listed in the SBOM. | Prevents a rogue plugin from loading hidden state. | Container with `--read-only` filesystem, `--cap-drop=ALL`. |
| **Package (code)** | The broker core **does not import** any module that writes to persistent storage. The memory‑layer is a separate package that *only* implements the *source‑connector* interface. | Guarantees architectural separation – the core cannot accidentally cache mutable data. | Build rules (e.g., `go vet -mod=readonly`, `cargo deny`) that forbid `broker-core` from depending on `broker-memory`. |

**Combination for different adoption contexts**

* **Solo developer** – Only the **dependency** layer matters.  The developer can `pip install broker-core` and be assured that no durable memory is present because the package is not in the environment.  The credential layer can be a simple “no‑token” placeholder; the broker will still function (it just reads public Git data).  
* **Small team** – Add **process** isolation (run the broker in a Docker container) and **credential** scoping.  The team can optionally add `broker-memory` to the lock‑file; the SBOM will then list it, making the presence explicit.  
* **Regulated enterprise** – Enforce **all four layers**: SBOM audit (no memory unless approved), container sandbox with read‑only mounts, and a dedicated read‑only service account for each source connector.  Policy tooling can automatically reject any deployment that lacks the “memory‑absent” flag when the organization wants a pure‑stateless audit.

Thus the **capability boundary** lives at the **dependency graph** (SBOM) combined with **runtime credential scoping**; the other layers are defensive hardening that can be toggled as needed.

---

## 3. Does “Durable‑as‑a‑Read‑Source” Actually Hold?

When the memory layer registers itself as a **source connector** (e.g., `memory://team‑principles`) the broker treats it exactly like a GitHub or Jira source:

1. **Input** – The broker receives a *snapshot* of the memory store (the latest git commit hash, plus a deterministic extraction of the stored cards).  
2. **Processing** – The broker calls the connector’s `Extract(sessionID, features)` function, which must be **pure**: given the same commit hash and the same feature flags, it returns identical cards.  
3. **Output** – The broker merges the cards with those from other connectors, builds a coverage certificate, and returns it.

**Where a leak could appear**

| Leak type | How it manifests | Why it breaks the guarantee |
|----------|-----------------|-----------------------------|
| **Implicit caching** | The broker, to improve latency, stores the result of the memory‑connector call in a local in‑process cache that survives across broker invocations. | The broker is no longer a pure function of current source state; stale cached cards could be returned, violating deterministic re‑derivability. |
| **Stateful error handling** | The broker records “failed to read memory store” flags in a global variable and suppresses future reads for that session. | This introduces hidden mutable state that influences future outputs, again breaking the pure‑function model. |
| **Write‑back side‑effects** | The memory connector, in order to “normalize” data, writes a canonical version of a card back to its git store when queried. | The read‑only contract of the broker is violated because a read request triggers a write, creating a poisonable feedback loop. |

If the **memory layer itself** is a *pure read source*, i.e., it never writes, never caches across calls, and its API is limited to “given commit hash → deterministic card set”, then the broker’s structural guarantees **remain intact**.  The coverage certificate will still list the memory source as “observed” and will be auditable because the broker can be re‑run with the same commit hash and produce the same certificate.

**Concrete safeguard:** The broker core must enforce that every connector implements an interface that **exposes only a stateless `extract` function** and **does not expose any mutable handles** (e.g., file descriptors that remain open).  A static analysis rule (e.g., `golangci-lint` rule `no-stateful-connector`) can be used to verify this property for any third‑party connector, including the memory layer.

---

## 4. When the Two‑Package Hybrid Collapses Back to “One Product”

**Failure mode:** *“Implicit coupling via shared runtime state”* – the broker core imports the memory package just to obtain a convenience function (e.g., `LoadTeamPrinciples()`) and stores the result in a global variable that is then used by all subsequent broker calls.

*Symptoms* –  
* The SBOM still shows `broker-memory` absent, yet the deployed binary contains the memory‑layer code.  
* Auditors cannot prove the system is stateless because the broker binary includes durable logic.  
* Upgrades to the memory store (e.g., a new PR) are not reflected until the broker process restarts, indicating hidden caching.

**Design rule that prevents it:** **“The broker core must have zero transitive dependencies on any durable‑state package.”** Enforced by:

1. **Build‑time isolation** – The core’s `go.mod`/`Cargo.toml`/`package.json` must declare *no* dependency on the memory package. CI can enforce this with a “no‑import‑from‑memory” lint rule.  
2. **Runtime contract** – The broker only receives connectors via a *registration* API (`broker.RegisterSource(connector)`). The memory package registers itself *outside* the broker process (e.g., via a side‑car that feeds JSON over the MCP). The broker never imports the memory code; it merely consumes its output.  
3. **Versioned SBOM verification** – Deployments are scanned; if any symbol from the memory package appears in the broker binary, the build is rejected.

When those rules are in place, the two packages remain **architecturally distinct** even though they are shipped together.  The only way the hybrid “collapses” is if a developer deliberately violates the registration contract, something that can be caught early by static analysis and SBOM gating.

---

### Bottom Line

*Publish a **specification + reference implementation** that is **stateless** by design.  The optional durable memory layer is just another **read‑only source connector** that lives in a separate package and is wired in via the same deterministic interface.  Enforce the stateless/durable seam through **dependency‑graph visibility (SBOM)** and **read‑only credential scoping**, optionally hardened with process sandboxing.  As long as the memory layer remains a pure data source, the broker’s guarantees of “no tracking, no poisonable state, full re‑derivability” hold.  The only collapse risk is an implicit import of the memory code into the broker core; a strict “no‑transitive‑dependency” rule eliminates that risk, preserving the two‑package architecture while delivering a single, extensible platform.*