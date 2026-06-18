Enumerate context events that should reach an AI coding agent at the START of a
unit of work (a new branch, or resuming a session) — for both solo developers and
enterprise teams. This tests whether a DETERMINISTIC, STRUCTURAL context broker is
sufficient, or whether it's "just a high-latency grep tool."

Be diverse and ADVERSARIAL. Deliberately include the hardest cases that a purely
structural broker would MISS. A "structural" broker knows ONLY explicit graph
edges: file/symbol overlap with open PRs, the changed-since-branch state of LINKED
tickets/docs, required checks/review gates, dependency edges, and superseded
versions. It does NOT learn, does NOT track usage, and does NOT do semantic/fuzzy
matching.

For EACH event output one row, pipe-delimited:
  id | one-line description | CLASS | one-line justification

CLASS is exactly one of:
  S (Structural) — catchable by a deterministic rule over explicit edges
      (same file/symbol overlap, linked ticket/doc changed since branch point,
       missing required check, dependency edge, superseded version).
  L (Learned/Semantic) — needs fuzzy/semantic relevance or a usage feedback loop
      (e.g. a conceptually-related but UNLINKED RFC; "files often changed together";
       tribal knowledge that was never written into a linked artifact).
  D (Declared) — catchable only via durable, human-declared config/policy
      (e.g. "payments/ requires finance review"; "this module is frozen").

Rules:
- Produce 16–20 events spanning solo + enterprise.
- You MUST include several genuine L cases. Do NOT inflate S to flatter the
  structural design. Classify honestly and adversarially.

Then finish with TWO lines:
  FRACTION: your honest estimate of the share of real-world HIGH-VALUE work-start
    context events in each class, as S=__% L=__% D=__% (sum 100).
  BIGGEST_MISS: the single most important thing a structural-only broker misses.
