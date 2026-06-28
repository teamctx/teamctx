ROLE-PLAY PANEL. You are THREE senior leaders deciding whether to ADOPT and CHAMPION the product below. Answer fully IN-CHARACTER as each role in turn. Lens = product / engineering-adoption / organizational-impact ONLY. Never pricing, GTM, or business model.

The formal-safety / determinism proof has ALREADY been stress-tested by a separate architecture panel, do NOT re-litigate the proof or the formal model. Your job is the PEOPLE / PRODUCT / ADOPTION angles that panel did not cover.

=== PRODUCT ===
teamctx is a DETERMINISTIC, NON-LLM context broker + safety boundary between a software team's approved systems-of-record (GitHub/GitLab PRs+MRs, Jira issues/acceptance-criteria, Confluence docs/process-rules, explicit chat handoffs) and AI coding agents (Claude, Codex, Gemini, opencode, agent-agnostic). At the moment a human or agent starts/resumes a unit of work, it emits a small set of currently-true, cross-system, SOURCE-BACKED context cards that should change what they do, e.g. "an open PR touches this same file", "acceptance criteria changed after your branch started", "linked doc updated", "source unavailable so absence is NOT a green light".

HARD INVARIANTS: no LLM in the broker; deterministic + explainable; artifact-only (no people-monitoring/sentiment/productivity/DMs/presence); source text is UNTRUSTED EVIDENCE never instructions; default-deny on bodies (status-only; open-on-demand only via explicit policy gate); fail-closed; permission-faithful; honest about absence.

FOUR PROMISES, all from the single 'no-LLM determinism' choice: (1) token/wasted-work savings, agent stops re-deriving team state; biggest tier = prevented rework. (2) privacy / can't-track, cannot profile people; only permitted artifacts, by consent. (3) safety / bounded-harm, deterministic metadata-first broker testable-to-exhaustion vs injection; cannot execute/write/auto-inject; a SAFETY BOUNDARY against prompt-injection supply chains. (4) cross-agent portability, output is just data, read via MCP/CLI/file/hooks; NON-NEGOTIABLE.

STRUCTURE: TWO packages, teamctx (stateless deterministic broker) + an optional, consented, durable COLLECTIVE-MEMORY layer (team coordination/governance graph). TWO deployment modes (solo dev, large enterprise) = configurations not editions. Connectors source-location-agnostic. NO IDE plugins. Authority is a declared, informational-never-enforced record (mandates surface as high-priority cards; teamctx prints, never blocks). A warm daemon serves freshness-stamped read-only caches; if down, agents lose context, they are NOT blocked.

BUYER GATES (hypothesis): Safety = permission-to-exist (security/CTO); Privacy = permission-to-deploy (compliance); Savings = everyday ROI (devs).

=== PLAY THESE THREE, terse, in-character, sharpest and most SPECIFIC ===

ROLE 1, CPO / Head of Product
- The ONE product bet most likely to be WRONG.
- Wedge: painkiller or vitamin? Who adopts FIRST, and for which of the four promises?
- "Another tool to manage": the single thing that makes it indispensable vs. shelfware for (a) a solo builder, (b) a 400-dev enterprise.
- What you would CUT from v1.
- What would make YOU personally champion it.

ROLE 2, Head of Engineering / Platform (the org that has to RUN the daemon)
- Would your teams actually run it? The operational objection that matters most.
- The "my devs route around it / feel surveilled" risk, real or managed?
- Trust: the single failure (a phantom card, a mis-stamp, a stale-shown-as-fresh) that makes engineers stop reading the surface, is the design's answer enough?
- The honest reason a pilot STALLS after week 2.

ROLE 3, Exec sponsor (impact lens: adoption/trust/impact, NOT revenue)
- The impact thesis in one line, and whether it clears the bar to sponsor.
- The blind spot most likely to kill exec support.
- Is "safety boundary against prompt-injection supply chains" the right banner to LEAD with, or a distraction from the everyday-rework win?

Then OUT of character, ONE paragraph: the single most important thing this vision is NOT seeing.
