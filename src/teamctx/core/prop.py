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
    "issue_criteria_changed": "existential",
    "no_criteria_changed_for_issues": "universal",
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
    args: tuple[str, ...] = ()  # opaque claim metadata (e.g. PR sig); not used in polarity

    @property
    def shape(self) -> PropShape:
        try:
            return PREDICATE_REGISTRY[self.predicate]
        except KeyError as exc:
            raise ValueError(f"unregistered predicate: {self.predicate!r}") from exc


Witness = Literal["supports", "refutes", "unrelated"]

# Each pair is (card_predicate, query_predicate): a card asserting card_predicate REFUTES
# the universal query_predicate when they share a repo and at least one subject item. Card
# kinds register their pair here as they are added.
REFUTES_PAIRS: frozenset[tuple[str, str]] = frozenset(
    {
        ("pr_conflicts_with_path", "no_pr_conflicts_with_paths"),
        ("issue_criteria_changed", "no_criteria_changed_for_issues"),
    }
)


def witnesses(claim: Prop, query: Prop) -> Witness:
    """Does a card's ``claim`` witness ``query`` (supports), its negation (refutes), or
    neither (unrelated)? Deterministic over typed structure only.

    A registered ``(claim.predicate, query.predicate)`` refutes-pair, with a shared repo and
    overlapping subject items, refutes the (universal) query. ``supports`` is reserved for
    kinds whose claim establishes a query directly.
    """

    if (
        (claim.predicate, query.predicate) in REFUTES_PAIRS
        and claim.subject.repo == query.subject.repo
        and set(claim.subject.paths) & set(query.subject.paths)
    ):
        return "refutes"
    return "unrelated"
