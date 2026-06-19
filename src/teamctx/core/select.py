"""Deterministic card derivation from source signals + the request context.

This is the broker's heart: it DERIVES context cards from typed source signals by
computing structural relevance against the request, rather than rendering authored cards.
Pure and deterministic — no I/O, time, or randomness (enforced by the core purity test) —
so every derived card is replayable and its reason names the overlap it came from.
"""

from __future__ import annotations

from collections.abc import Callable, Iterable
from dataclasses import dataclass
from typing import Literal

from teamctx.core.contracts import ContextCard, RequestContext, SourceSignal, SourceStatus
from teamctx.core.prop import Prop, SubjectRef

Delta = Literal["none", "count", "identity"]


@dataclass(frozen=True)
class Hint:
    """An untrusted, uncertified best-effort guess (the H layer).

    H is **outside the privacy contract**: a hint must be projected to the consumer-visible
    set before it is ever surfaced to a human, and it carries NO certificate weight — it
    never enters the certified card set C. No hint producers exist yet; the layer is kept
    structurally separate so certified and uncertified context never share a channel.
    """

    subject: str
    summary: str
    source: str


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
    """Derive typed claims from the P-visible signals, dispatching by registered card kind."""

    claims: list[ClaimCard] = []
    for signal in project_visible_signals(signals):
        kind = _KIND_BY_SIGNAL_TYPE.get(signal.signal_type)
        if kind is None:
            continue
        claim_card = kind.derive(request, signal)
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


@dataclass(frozen=True)
class CardKind:
    """One registered card kind: how to derive it, what universal it refutes, how to render
    it. New kinds are added by appending an entry — the engine's control flow is unchanged."""

    signal_type: str
    card_predicate: str
    derive: Callable[[RequestContext, SourceSignal], ClaimCard | None]
    query: Callable[[RequestContext], Prop]
    render: Callable[[ClaimCard], ContextCard]


CARD_KINDS: tuple[CardKind, ...] = (
    CardKind(
        signal_type="collision",
        card_predicate="pr_conflicts_with_path",
        derive=_derive_collision_claim,
        query=no_conflict_query,
        render=render_collision_claim,
    ),
)

_KIND_BY_SIGNAL_TYPE: dict[str, CardKind] = {kind.signal_type: kind for kind in CARD_KINDS}
_RENDER_BY_PREDICATE: dict[str, Callable[[ClaimCard], ContextCard]] = {
    kind.card_predicate: kind.render for kind in CARD_KINDS
}


def render_claim(claim_card: ClaimCard) -> ContextCard:
    """Render a claim card via its kind's renderer (dispatch on the card predicate)."""

    return _RENDER_BY_PREDICATE[claim_card.claim.predicate](claim_card)


def derive_cards(request: RequestContext, signals: Iterable[SourceSignal]) -> list[ContextCard]:
    """Derive context cards: typed claims rendered via their kind's renderer."""

    return [render_claim(claim_card) for claim_card in derive_claims(request, signals)]


def _is_surfaceable(signal: SourceSignal) -> bool:
    """Fail-closed: never surface a signal the requester is not permitted to see at all."""

    if signal.visibility in {"hidden", "never"}:
        return False
    return signal.policy.can_render_to_user


def project_visible_signals(signals: Iterable[SourceSignal]) -> list[SourceSignal]:
    """Project signals to the consumer-visible set (Delta_P): drop any the requester may not
    see at all. Selection runs over this projection only, so a P-invisible signal cannot
    affect the observable (Theorem 5: existence-privacy)."""

    return [signal for signal in signals if _is_surfaceable(signal)]


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
    delta: Delta = "none"


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


def build_coverage(statuses: Iterable[SourceStatus], delta: Delta = "none") -> Coverage:
    """Record each observed source's status verbatim, with the declassification dial. The
    dial defaults to ``none``; ``count``/``identity`` declassification of invisible-target
    dangling references is deferred until reference-target tracking exists."""

    entries = tuple(
        CoverageEntry(
            source_id=status.source_id,
            source_family=status.source_family,
            status=status.status,
            last_checked_at=status.last_checked_at,
        )
        for status in statuses
    )
    return Coverage(entries=entries, delta=delta)


@dataclass(frozen=True)
class ContextSelection:
    """The broker's answer at work-start: rendered cards, the typed certified claims (C), the
    untrusted hint layer (H), honest coverage, and per-proposition closure."""

    cards: tuple[ContextCard, ...]
    claim_cards: tuple[ClaimCard, ...]
    hints: tuple[Hint, ...]
    coverage: Coverage
    closure: tuple[ClosureEntry, ...]


def select_context(
    request: RequestContext,
    signals: Iterable[SourceSignal],
    statuses: Iterable[SourceStatus],
) -> ContextSelection:
    """Broker entry point: derive typed claims, render cards, report coverage + per-kind closure."""

    coverage = build_coverage(statuses)
    claim_cards = tuple(derive_claims(request, signals))
    cards = tuple(render_claim(claim_card) for claim_card in claim_cards)
    closure = tuple(
        ClosureEntry(
            proposition=kind.query(request).predicate,
            status=assess_completeness(kind.query(request), coverage),
        )
        for kind in CARD_KINDS
    )
    return ContextSelection(
        cards=cards,
        claim_cards=claim_cards,
        hints=(),
        coverage=coverage,
        closure=closure,
    )
