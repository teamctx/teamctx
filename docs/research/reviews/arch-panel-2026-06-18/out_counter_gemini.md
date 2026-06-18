This "consensus" is a textbook example of architectural over-engineering designed to solve PR problems rather than engineering ones. It’s a distributed systems fairy tale. Here is why it breaks.

### 1. The Protocol Trap: Standardizing the Wrong Layer
Shipping a "specification + reference implementation" is the fastest way to ensure the "deterministic" guarantee never actually exists. Context is inherently fuzzy; it relies on how you parse a Jira ticket, how you truncate a long file, and how you resolve a symbolic link in a monorepo. 

As soon as you decentralize the engine, you get **semantic drift**. Two "compatible" brokers will interpret the same GitHub PR slightly differently based on their internal regexes or API timeout handlings. For an AI agent, a 1% difference in context is a 100% difference in the generated code's logic. If you want determinism, you don't ship a protocol; you ship a **canonical, bit-for-bit reproducible binary**. The "standard" should be the output schema, period.

### 2. SBOM Security is Governance Theater
The idea that "memory package absent = provably can't retain" is cute, but any real security reviewer will laugh. If the broker has a "generic source interface" that can talk to HTTPS (GitHub/Jira), it has an **exfiltration path**. 

A developer doesn't need a "memory package" to persist state; they just need an environment variable pointing to a sidecar proxy or a malicious "source connector" that logs every query. The security boundary isn't the lockfile; it's the **credential scope and network egress**. Marketing the SBOM as a "capability-proof" creates a false sense of security that will be shattered the moment a custom "connector" is used to bridge data to an unvetted endpoint.

### 3. The "Durable-as-a-Read-Source" Leak
The "read-only memory" theory collapses on the **Relevance Problem**. In practice, you cannot have a "generic source interface" for memory without the broker understanding *how to query it*. 

If the broker treats memory like GitHub, it’s going to request "everything relevant." But who defines relevance? If the memory layer does the ranking, it's performing "query-driven computation," which is a form of hidden state. If the broker does the ranking, it needs to pull a massive index over the wire. You’ll end up with "leaky abstractions" where the broker starts needing specific flags to handle the latency and structure of the memory layer, or it will be too slow to use.

### 4. The Grand Blind Spot: The I/O Storm (Latency)
All four models missed the **Performance Tax of Honesty**. 

To provide a "Coverage Certificate" that is actually "honest," a stateless broker must verify the state of every connected source (GitHub, Jira, Slack, Memory) on *every single request*. You are creating a massive **N+1 I/O problem**. 

If the broker is truly stateless and forbids caching (to stay "pure"), the latency for a single context fetch will be the sum of your slowest API's tail latency. No developer will use a tool that adds 4 seconds of "verification overhead" to every prompt just to prove it didn't look at a database it doesn't have.

**The most fragile part?** Point 4. A broker that is "fully useful without memory" but has "zero knowledge" of it is a broker that will provide garbage context. Without a feedback loop (memory) to tell the broker which files were actually useful in the last turn, the "stateless" broker is just a high-latency grep tool.
