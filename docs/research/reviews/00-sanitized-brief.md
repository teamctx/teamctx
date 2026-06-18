PRODUCT: teamctx - a DETERMINISTIC, NON-LLM context broker + safety boundary between a software team's approved systems-of-record (GitHub/GitLab PRs+MRs, Jira issues/acceptance-criteria, Confluence docs/process-rules, explicit chat handoffs) and AI coding agents (Claude, Codex, Gemini, opencode - agent-agnostic). At the moment a human or agent starts/resumes a unit of work, it emits a small set of currently-true, cross-system, SOURCE-BACKED context cards that should change what they do - e.g. "an open PR touches this same file", "acceptance criteria changed after your branch started", "linked doc updated", "source unavailable so absence is NOT a green light".

HARD INVARIANTS: no LLM in the broker; deterministic + explainable; artifact-only (no people-monitoring/sentiment/productivity/DMs/presence); source text is UNTRUSTED EVIDENCE never instructions; default-deny on bodies (status-only; open-on-demand only via explicit policy gate); fail-closed; permission-faithful; honest about absence.

FOUR PROMISES, all derived from the single 'no-LLM determinism' choice:
1) Token / wasted-work savings (agent stops re-deriving team state every session; biggest tier = prevented rework).
2) Privacy / "can't track" (cannot profile people; only permitted work artifacts, by consent).
3) Safety / harm-incapability (deterministic metadata-first broker is testable-to-exhaustion vs injection/malware; un-injectable; cannot execute/write/auto-inject). Reframes product as a SAFETY BOUNDARY against prompt-injection supply chains.
4) Cross-agent portability (output is just data so every agent reads it via MCP/CLI/file/hooks/thin adapters). NON-NEGOTIABLE.

STRUCTURE: TWO packages - teamctx (stateless deterministic broker; value-prop A 'agent-context surface') + Ambara (optional, consented, durable COLLECTIVE-MEMORY layer; value-prop B 'team coordination/governance graph'). TWO deployment modes (solo dev, large enterprise) = configurations not editions. Connectors source-location-agnostic (cloud or self-hosted = config).
SCOPE: GitHub+GitLab+Jira+Confluence first-class; horizontal (all software teams); NO IDE plugins; deployment model + cloud-vs-self-hosted-sources left open.
BUYER GATES: Safety = permission-to-exist (security/CTO); Privacy = permission-to-deploy (compliance); Savings = everyday ROI (devs/budget).

Give your sharpest, most SPECIFIC critique. Disagree freely. Terse bullets under each heading:
1) WHAT KILLS THIS: top 3 risks/blind spots.
2) THE DETERMINISM BET: is 'no-LLM deterministic' a durable moat, or will LLM-native context + bigger context windows make it irrelevant? Steelman the counter.
3) WEAKEST WEDGE: is 'safety boundary' a painkiller or a vitamin? Who pays FIRST, for which promise?
4) AMBARA vs PRIVACY: is a consented collective graph credible at enterprise scale, or fundamentally in tension with 'can't track'?
5) DAY-IN-THE-LIFE: the single most important thing to nail for (a) a solo builder and (b) a large enterprise team, so it is indispensable not another tool to manage.
6) BLIND SPOT: the most important thing this vision is NOT seeing.