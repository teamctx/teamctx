"""Deterministic severity decomposition for cards (calibration deferred).

severity = clamp01(kind_base × (1 + ALPHA·magnitude_norm) × scope_mult). The decomposition
is retained on the card for audit and conformance: any conforming broker computes identical
numbers for identical inputs. The constants are placeholder defaults; calibration needs
deployment telemetry (out of scope here). The per-kind base is passed in by the caller (the
card-kind registry in ``core/kinds.py`` owns it); this module is the pure mechanism. Pure: no
I/O.
"""

from __future__ import annotations

from teamctx.core.contracts import Severity
from teamctx.core.prop import Prop

ALPHA = 0.5
_MAGNITUDE_NORM_DIVISOR = 5.0


def compute_severity(kind_base: float, claim: Prop) -> Severity:
    """Compute the severity decomposition for a card from its per-kind base. Magnitude is the
    fan-out (number of subject items), normalized and clamped to [0, 1]; scope_mult is 1.0 for
    now."""

    magnitude_norm = round(min(1.0, len(claim.subject.paths) / _MAGNITUDE_NORM_DIVISOR), 4)
    scope_mult = 1.0
    value = round(min(1.0, kind_base * (1 + ALPHA * magnitude_norm) * scope_mult), 4)
    return Severity(
        value=value, kind_base=kind_base, magnitude_norm=magnitude_norm, scope_mult=scope_mult
    )
