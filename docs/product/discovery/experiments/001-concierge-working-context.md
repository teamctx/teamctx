# E-001 Concierge Working Context

## Question

If TeamCtx existed today, what working context should appear at the start or
resume point of a real agent-terminal session?

## Hypothesis

A small, sourced packet will help the human and agent keep moving if it contains
only:

- live risks that affect the current work
- saved guidance that applies to the current scope
- stale or missing sources that change confidence
- exact source references and reasons

It will fail if it feels like search results, project documentation, surveillance,
or a second task to manage.

## Method

Run a concierge version before automation:

1. The CPO gives the CTO a real task or resume point.
2. The CTO manually inspects approved sources already available in the workspace.
3. The CTO writes a simulated terminal context surface for what the user would
   actually see.
4. The CTO writes an internal working-context packet for evaluation notes.
5. The CPO and agent use or react to the simulated terminal surface.
6. Record whether each item helped, distracted, was missing, or was unsafe.

## Packet Format

Use two artifacts:

- [terminal-context-surface.md](../templates/terminal-context-surface.md) for
  the user-facing simulation.
- [working-context-packet.md](../templates/working-context-packet.md) for
  internal evaluation notes.

The packet is an internal concierge evaluation artifact. It is not the final
terminal UI, not command syntax, and not vocabulary a user is expected to type.
The simulated terminal surface should fit in one terminal screen whenever
possible.

Required sections:

- `Heads up`
- `Saved guidance`
- `Source health`
- `Not used`

Optional sections:

- `Open questions`
- `Keep for future candidate`

## Metrics

Primary:

- Did it prevent a lookup?
- Did it prevent a mistake?
- Did it reduce repeated explanation?
- Did any item distract or overreach?

Secondary:

- Time saved estimate.
- Token saved estimate.
- Number of source checks avoided.
- Number of stale/missing sources surfaced.

## Pass Criteria

After 5 real sessions:

- At least 3 sessions have a clear saved lookup, avoided mistake, or reduced
  repeated explanation.
- Fewer than 20 percent of shown items are judged distracting or irrelevant.
- No item exposes private, blocked, or unsupported source content.
- User-facing language works without explaining TeamCtx internals.

## Fail Criteria

- The packet mostly restates obvious repo/task facts.
- The user has to learn internal terms to act.
- The user thinks packet headings are commands or required product vocabulary.
- Useful context requires broad search or raw source dumps.
- The user distrusts or ignores source health.
- The packet makes the agent over-trust stale or advisory context.

## Decision

Pending.
