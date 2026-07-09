"""Typed propositions: the broker's claims, with polarity.

A card does not assert free text; it asserts a typed ``Prop`` and *witnesses* it. Whether a card
witnesses a consumer's query proposition or its negation is a deterministic relation over typed
structure, never a reading of payload. This module owns the pure datatypes (``Prop``,
``SubjectRef``) and the parameterized witness mechanism (``witnesses_with``); which predicate
pairs refute each other, and under which match rule, is registered per card kind in
``core/kinds.py``. This is the seam the consumer SDK and observable soundness (Theorem 2) build
on.

Pure: dataclasses and typing only, no I/O, time, or randomness (the core purity test
guards this).
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Literal

PropShape = Literal["universal", "existential"]


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


Witness = Literal["supports", "refutes", "unrelated"]

# The structural overlap a refutation requires: ``subject-overlap`` needs a shared repo and at
# least one shared subject item; ``repo-wide`` needs a shared repo alone. Each card kind picks
# one (registered in ``core/kinds.py``).
RefutesMatch = Literal["subject-overlap", "repo-wide"]


def witnesses_with(claim: Prop, query: Prop, match: RefutesMatch) -> Witness:
    """Does ``claim`` witness ``query``'s negation (refutes) under the given match rule, or
    neither (unrelated)? Deterministic over typed structure only.

    ``match`` selects the structural overlap a refutation requires: ``subject-overlap`` needs a
    shared repo and at least one shared subject item (the original collision rule); ``repo-wide``
    needs a shared repo alone. ``supports`` is reserved for kinds whose claim establishes a query
    directly; this mechanism never returns it.
    """

    if claim.subject.repo != query.subject.repo:
        return "unrelated"
    if match == "repo-wide":
        return "refutes"
    if set(claim.subject.paths) & set(query.subject.paths):
        return "refutes"
    return "unrelated"
