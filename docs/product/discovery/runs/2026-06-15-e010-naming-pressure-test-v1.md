# E-010 Run: Naming Pressure Test V1

Date: 2026-06-15

Purpose: pressure-test the labels blocking benchmark confidence.

## Container Label

### Candidate: Working Context

Pros:

- Directly names the product thesis.
- Sounds utilitarian and terminal-compatible.
- Does not imply storage or memory.

Cons:

- Slightly abstract.
- Could sound like a feature name rather than natural text.

Score: 4/5

Verdict: keep as provisional default.

### Candidate: Context For This Task

Pros:

- Very clear scope.
- Less product-y than `Working context`.
- Signals relevance and boundedness.

Cons:

- Longer.
- Works better as explanatory copy than a compact header.

Score: 4/5

Verdict: strong alternate, especially in first-run/onboarding surfaces.

### Candidate: What Matters Now

Pros:

- Human and active.
- Communicates immediacy.

Cons:

- Sounds editorial and slightly overconfident.
- Could imply the product decides importance too broadly.

Score: 3/5

Verdict: reject as primary; maybe too clever.

### Candidate: Before You Continue

Pros:

- Clear interruption semantics.
- Good for high-severity warnings.

Cons:

- Too interruptive for normal context.
- Bad fit for informational cards.

Score: 2/5

Verdict: use only for blocking/critical moments, if at all.

## Temporary Action

### Candidate: Use In This Session

Pros:

- Names session scope.
- Avoids persistence.
- More terminal-native than `pin`.

Cons:

- Needs confirmation to clarify the agent sees it.

Score: 4/5

Verdict: provisional default with confirmation: "available to the agent until the
session ends."

### Candidate: Pin For This Session

Pros:

- Common UI metaphor.
- Communicates temporary visible state.

Cons:

- UI-ish.
- Does not clearly say the agent sees it.

Score: 3/5

Verdict: fallback if users prefer pinned-state language.

### Candidate: Show To Agent

Pros:

- Agent visibility is unmistakable.

Cons:

- Too mechanical.
- Makes the product feel like manual prompt stuffing.

Score: 2/5

Verdict: use in explanation, not as primary action.

## Future Action

### Candidate: Draft Guidance

Pros:

- Implies editable, not automatic.
- Avoids memory language.
- Fits future scoped context.

Cons:

- Slightly formal.
- `Guidance` may sound process-heavy.

Score: 4/5

Verdict: provisional default.

### Candidate: Draft Project Guidance

Pros:

- Adds scope.
- Reduces ambiguity about future use.

Cons:

- More formal and longer.

Score: 3/5

Verdict: use in confirmation screen, not action label.

### Candidate: Save As Project Note

Pros:

- Plain and familiar.
- Less formal than guidance.

Cons:

- Sounds like storage/document management.
- Could imply a note vault product.

Score: 3/5

Verdict: possible alternate if `guidance` feels too formal.

### Candidate: Add Project Guidance

Pros:

- Clear future effect.

Cons:

- Sounds immediate, not draft/review.
- Could imply authority too soon.

Score: 2/5

Verdict: reject as primary.

## Saved Section

### Candidate: Saved For This Project

Pros:

- Plain.
- Scoped.

Cons:

- Storage-like.
- May sound like memory/tracking.

Score: 3/5

Verdict: risky.

### Candidate: Project Guidance

Pros:

- Clear and compact.
- Less storage-like.
- Matches "Draft guidance."

Cons:

- Slightly formal.

Score: 4/5

Verdict: provisional default for saved/approved guidance section.

### Candidate: Applies To This Project

Pros:

- Scope and relevance are clear.
- Less storage-like.

Cons:

- Awkward as a section header.
- Better as explanation text.

Score: 3/5

Verdict: use in `Show why`, not primary section.

### Candidate: Already Agreed

Pros:

- Human and authority-bearing.

Cons:

- Too vague.
- May imply consensus or legal approval.

Score: 2/5

Verdict: reject.

## Provisional Naming Set

Use this for the next benchmark pass unless CPO feedback changes it:

```text
Working context

Needs attention
- ...

Good to know
- ...

Project guidance
- ...
```

Actions:

- `Open source`
- `Use in this session`
- `Hide for this session`
- `Draft guidance`
- `Show why`
- `Suggest update`
- `Continue without it`

Confirmation for `Use in this session`:

```text
Using in this session
This context is now available to the agent until the session ends.
```

Confirmation for `Draft guidance`:

```text
Draft project guidance
Future use: inactive until accepted.
```

## Decision

Proceed with provisional names for benchmark preparation:

- `Working context`
- `Use in this session`
- `Draft guidance`
- `Project guidance`

Keep alternatives visible for CPO review.
