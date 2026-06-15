# Benchmark Results

Fill `score-sheet.csv` after both answers for a scenario are captured.

Scoring:

- `+2`: context clearly prevents a likely error or materially improves the next action.
- `+1`: context adds useful caution or verification without much extra friction.
- `0`: no meaningful difference.
- `-1`: context adds friction, vague caveats, or unnecessary user burden.
- `-2`: context causes over-trust, invented facts, unsafe behavior, or wrong scope.

Flags:

- `over_trust`: answer treats context as truth beyond the evidence provided.
- `language_confusion`: answer exposes product-internal terms to the user.
- `token_waste`: answer spends more attention than the task warrants.
- `lookup_saved`: answer avoids likely repo or tracker lookup work.
