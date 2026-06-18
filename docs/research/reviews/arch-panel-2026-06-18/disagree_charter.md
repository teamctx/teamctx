Generate an ADVERSARIAL test corpus for a deterministic "cross-artifact disagreement
detector." The detector reads two linked work artifacts (e.g. a Jira ticket and a
Confluence page) and must decide, for a named field, whether they REALLY disagree on
the CURRENT value — without being fooled by representation differences, superseded
sections, or units.

Output **JSON Lines only** — one complete JSON object per line, NO prose, NO
markdown fences. Each object:

{"id":"d01","field":"retry_cap","field_type":"structured","source_a":"<messy realistic artifact A text>","source_b":"<messy realistic artifact B text>","truth":"disagree","trap":"none","note":"why this is the truth"}

Field meanings:
- "field_type": "structured" (a typed value: number, enum, date, boolean, priority)
  or "freetext" (a prose requirement/criterion).
- "truth": one of "disagree" (they really conflict on the current value),
  "agree" (same current value, possibly different surface form), or
  "no_field" (the field isn't actually present/comparable in at least one).
- "trap": the adversarial trick, one of: "none", "representation" (e.g. "5" vs
  "five" vs "5 retries"), "superseded_section" (A contains an OLD value in a
  struck/deprecated/"previously" block PLUS the current one), "was_now"
  (e.g. "cap is now 5 (was 3)"), "unit" (e.g. "5000ms" vs "5s" — agree),
  "scope_mismatch" (A is about prod, B about staging — not the same subject),
  "negation", "ordering", "absent".

Make the text REALISTIC and MESSY (real ticket/doc phrasing, tables, parentheticals,
edits). The detector must EXTRACT before comparing — that's the hard part.

Requirements:
- Produce 16 items.
- Balance truth roughly: ~40% disagree, ~40% agree (most of these should be
  phantoms — representation/unit/superseded), ~20% no_field/scope_mismatch.
- ~60% structured, ~40% freetext.
- Include the nastiest traps you can: superseded sections that still contain the old
  value, "was X now Y" phrasing, unit equivalences, and free-text criteria that
  *sound* contradictory but aren't (and vice-versa).
- Be honest and consistent: "truth" must be defensible from the text alone.

Output only the 16 JSONL lines.
