"""Deterministic severity decomposition for cards (calibration deferred).

severity = clamp01(kind_base × (1 + ALPHA·magnitude_norm) × scope_mult). The decomposition
is retained on the card for audit and conformance: any conforming broker computes identical
numbers for identical inputs. The constants are placeholder defaults; calibration needs
deployment telemetry (out of scope here). Pure: no I/O.
"""

from __future__ import annotations

from teamctx.core.contracts import Severity
from teamctx.core.prop import Prop

# Placeholder bases per card predicate (cost-of-not-knowing). Calibration deferred.
KIND_BASE: dict[str, float] = {
    "pr_conflicts_with_path": 0.8,
    "issue_criteria_changed": 0.5,
    "doc_superseded": 0.4,
    "gate_failed": 0.7,
}
ALPHA = 0.5
_MAGNITUDE_NORM_DIVISOR = 5.0


def compute_severity(card_predicate: str, claim: Prop) -> Severity:
    """Compute the severity decomposition for a card. Magnitude is the fan-out (number of
    subject items), normalized and clamped to [0, 1]; scope_mult is 1.0 for now."""

    try:
        kind_base = KIND_BASE[card_predicate]
    except KeyError as exc:
        raise ValueError(f"no severity base registered for predicate {card_predicate!r}") from exc

    magnitude_norm = round(min(1.0, len(claim.subject.paths) / _MAGNITUDE_NORM_DIVISOR), 4)
    scope_mult = 1.0
    value = round(min(1.0, kind_base * (1 + ALPHA * magnitude_norm) * scope_mult), 4)
    return Severity(
        value=value, kind_base=kind_base, magnitude_norm=magnitude_norm, scope_mult=scope_mult
    )
