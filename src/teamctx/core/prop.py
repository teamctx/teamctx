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


Witness = Literal["supports", "refutes", "unrelated"]


def witnesses(claim: Prop, query: Prop) -> Witness:
    """Does a card's ``claim`` witness ``query`` (supports), its negation (refutes), or
    neither (unrelated)?

    Deterministic over typed structure only. For this build: an existential
    ``pr_conflicts_with_path`` claim *refutes* the universal ``no_pr_conflicts_with_paths``
    query whenever they share a repo and at least one path — a counterexample to "no
    conflict". ``supports`` is reserved for kinds whose claim establishes a query directly.
    """

    if (
        query.predicate == "no_pr_conflicts_with_paths"
        and claim.predicate == "pr_conflicts_with_path"
        and claim.subject.repo == query.subject.repo
        and bool(set(claim.subject.paths) & set(query.subject.paths))
    ):
        return "refutes"
    return "unrelated"
