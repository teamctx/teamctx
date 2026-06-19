"""Typed propositions: the broker's claims, with polarity.

A card does not assert free text; it asserts a typed ``Prop`` and *witnesses* it. Whether a
card witnesses a consumer's query proposition ``rho`` or its negation is a deterministic
relation over typed structure (``witnesses``), never a reading of payload. This is the seam
the consumer SDK and observable soundness (Theorem 2) build on.

Pure: dataclasses and typing only — no I/O, time, or randomness (the core purity test
guards this).
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Literal

PropShape = Literal["universal", "existential"]

# The predicates this build models, and their logical shape. A universal ("no PR conflicts
# with any of my paths") is refuted by a single counterexample; an existential ("a PR
# conflicts with this path") is witnessed by a single instance. Card kinds register their
# predicate here as they are added.
PREDICATE_REGISTRY: dict[str, PropShape] = {
    "pr_conflicts_with_path": "existential",
    "no_pr_conflicts_with_paths": "universal",
}


@dataclass(frozen=True)
class SubjectRef:
    """A typed reference to what a proposition is about. For collisions: a repo + paths."""

    repo: str
    paths: tuple[str, ...] = ()


@dataclass(frozen=True)
class Prop:
    """A typed proposition: a registered predicate over a subject, with typed arguments."""

    predicate: str
    subject: SubjectRef
    args: tuple[str, ...] = ()

    @property
    def shape(self) -> PropShape:
        try:
            return PREDICATE_REGISTRY[self.predicate]
        except KeyError as exc:
            raise ValueError(f"unregistered predicate: {self.predicate!r}") from exc
