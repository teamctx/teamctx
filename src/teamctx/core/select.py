"""Deterministic card derivation from source signals + the request context.

This is the broker's heart: it DERIVES context cards from typed source signals by
computing structural relevance against the request, rather than rendering authored cards.
Pure and deterministic — no I/O, time, or randomness (enforced by the core purity test) —
so every derived card is replayable and its reason names the overlap it came from.
"""

from __future__ import annotations

from collections.abc import Iterable
from dataclasses import dataclass
from typing import Literal

from teamctx.core.contracts import ContextCard, RequestContext, SourceSignal, SourceStatus
from teamctx.core.prop import Prop, SubjectRef


@dataclass(frozen=True)
class ClaimCard:
    """A derived typed claim paired with the source signal it was derived from.

    ``claim`` is the proposition the card asserts (and witnesses); ``signal`` carries the
    render inputs. The render card is a pure function of this pair (``render_collision_claim``).
    """

    claim: Prop
    signal: SourceSignal


def no_conflict_query(request: RequestContext) -> Prop:
    """The universal a collision card refutes: 'no open PR conflicts with my paths'."""

    return Prop(
        predicate="no_pr_conflicts_with_paths",
        subject=SubjectRef(repo=request.repo, paths=tuple(request.paths)),
    )


def derive_claims(
    request: RequestContext, signals: Iterable[SourceSignal]
) -> list[ClaimCard]:
    """Derive typed claims from signals by computing structural relevance to the request."""

    claims: list[ClaimCard] = []
    for signal in signals:
        if not _is_surfaceable(signal):
            continue
        if signal.signal_type == "collision":
            claim_card = _derive_collision_claim(request, signal)
            if claim_card is not None:
                claims.append(claim_card)
    return claims


def _derive_collision_claim(
    request: RequestContext, signal: SourceSignal
) -> ClaimCard | None:
    if signal.scope.get("repo") != request.repo:
        return None
    candidate_files = signal.scope.get("files")
    candidate = candidate_files if isinstance(candidate_files, list) else []
    shared = sorted(set(request.paths) & set(candidate))
    if not shared:
        return None
    claim = Prop(
        predicate="pr_conflicts_with_path",
        subject=SubjectRef(repo=request.repo, paths=tuple(shared)),
        args=(signal.id,),
    )
    return ClaimCard(claim=claim, signal=signal)


def render_collision_claim(claim_card: ClaimCard) -> ContextCard:
    """Render a collision claim into a human-plane ``ContextCard``.

    Pure: the render card is a function of the claim plus its signal. Output matches the
    pre-typed collision derivation byte for byte.
    """

    claim = claim_card.claim
    signal = claim_card.signal
    overlap = ", ".join(claim.subject.paths)
    return ContextCard(
        schema_version="teamctx.context_card.v0",
        id=f"card_{signal.id}",
        section="Needs attention",
        text=signal.evidence_summary,
        why_this_matters=f"you are editing {claim.subject.paths[0]}.",  # most-salient path
        source_display=signal.source_display,
        refs=[signal.id],
        reason=f"same repository and file path as the current task: {overlap}",
        scope=dict(signal.scope),
        freshness=signal.freshness,
        confidence=signal.confidence,
        source_body="status_only",
        source_open_target_id=None,
        agent_instruction="verify_before_relying",
    )


def derive_cards(request: RequestContext, signals: Iterable[SourceSignal]) -> list[ContextCard]:
    """Derive context cards: typed claims (derive_claims) rendered to cards
    (render_collision_claim).
    """

    return [render_collision_claim(claim_card) for claim_card in derive_claims(request, signals)]


def _is_surfaceable(signal: SourceSignal) -> bool:
    """Fail-closed: never surface a signal the requester is not permitted to see at all."""

    if signal.visibility in {"hidden", "never"}:
        return False
    return signal.policy.can_render_to_user


@dataclass(frozen=True)
class CoverageEntry:
    source_id: str
    source_family: str
    status: str
    last_checked_at: str | None


@dataclass(frozen=True)
class Coverage:
    """Honest report of what was checked. Absence of cards is never clearance."""

    entries: tuple[CoverageEntry, ...]


Completeness = Literal[
    "complete",
    "incomplete[dangling]",
    "incomplete[stale-dep]",
    "incomplete[policy-gap]",
    "incomplete[unbounded]",
    "incomplete[unmodeled-ref]",
]

# deps_G: the trusted, mandated source families a proposition's truth depends on. A
# predicate is registered here as its card kind is added. An unregistered predicate fails
# loud — we never silently certify a query whose dependencies we have not modeled.
DEPS_REGISTRY: dict[str, frozenset[str]] = {
    "no_pr_conflicts_with_paths": frozenset({"git_hosting"}),
}


def deps_for(prop: Prop) -> frozenset[str]:
    """The mandated source families whose state can affect ``prop`` (deps_G)."""

    try:
        return DEPS_REGISTRY[prop.predicate]
    except KeyError as exc:
        raise ValueError(
            f"no dependency closure registered for predicate {prop.predicate!r}"
        ) from exc


def assess_completeness(prop: Prop, coverage: Coverage) -> Completeness:
    """The paper's ``complete?``: is every mandated dependency of ``prop`` observed fresh?

    Returns ``incomplete[policy-gap]`` if a mandated source family is absent from coverage,
    ``incomplete[stale-dep]`` if present but not fresh, else ``complete``. The reasons
    ``dangling``/``unbounded``/``unmodeled-ref`` are defined but not yet emitted (they need
    reference-target / connector-schema structure introduced in later slices).
    """

    entries_by_family: dict[str, list[CoverageEntry]] = {}
    for entry in coverage.entries:
        entries_by_family.setdefault(entry.source_family, []).append(entry)

    stale_seen = False
    for family in sorted(deps_for(prop)):
        family_entries = entries_by_family.get(family, [])
        if not family_entries:
            return "incomplete[policy-gap]"
        if any(entry.status != "fresh" for entry in family_entries):
            stale_seen = True
    if stale_seen:
        return "incomplete[stale-dep]"
    return "complete"


@dataclass(frozen=True)
class ClosureEntry:
    """A per-proposition completeness status for the coverage certificate (kappa.closure)."""

    proposition: str
    status: Completeness


def build_coverage(statuses: Iterable[SourceStatus]) -> Coverage:
    """Summarize per-source coverage; any non-fresh source makes coverage incomplete."""

    entries = tuple(
        CoverageEntry(
            source_id=status.source_id,
            source_family=status.source_family,
            status=status.status,
            last_checked_at=status.last_checked_at,
        )
        for status in statuses
    )
    return Coverage(entries=entries)


@dataclass(frozen=True)
class ContextSelection:
    """The broker's answer at work-start: derived cards, honest coverage, and per-
    proposition closure."""

    cards: tuple[ContextCard, ...]
    coverage: Coverage
    closure: tuple[ClosureEntry, ...]


def select_context(
    request: RequestContext,
    signals: Iterable[SourceSignal],
    statuses: Iterable[SourceStatus],
) -> ContextSelection:
    """Broker entry point: derive cards, report coverage, and assess per-proposition closure."""

    coverage = build_coverage(statuses)
    query = no_conflict_query(request)
    closure = (
        ClosureEntry(proposition=query.predicate, status=assess_completeness(query, coverage)),
    )
    return ContextSelection(
        cards=tuple(derive_cards(request, signals)),
        coverage=coverage,
        closure=closure,
    )
