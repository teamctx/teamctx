"""The card-derivation engine: source signals + request context -> an honest selection.

This is the broker's heart: it DERIVES context cards from typed source signals by computing
structural relevance against the request, rather than rendering authored cards. The card kinds
themselves (how each is derived, what universal it refutes, how it renders, its cost and
dependencies) live in ``core/kinds.py``; this module is the engine that dispatches over
``CARD_KINDS`` and assembles coverage, closure, and the replayable selection. Pure and
deterministic: no I/O, time, or randomness (enforced by the core purity test), so every derived
card is replayable and its reason names the overlap it came from.
"""

from __future__ import annotations

from collections.abc import Callable, Iterable
from dataclasses import dataclass
from typing import Literal

from teamctx.core.authority import AuthorityDecl, AuthorityEntry, assess_authority
from teamctx.core.contracts import (
    ClosureEntry,
    ClosureStatus,
    ContextCard,
    RequestContext,
    SourceDocument,
    SourceSignal,
    SourceStatus,
)
from teamctx.core.kinds import CARD_KINDS, CardKind, ClaimCard, deps_for
from teamctx.core.prop import Prop
from teamctx.core.snapshot import snapshot_digest as _snapshot_digest

Delta = Literal["none", "count", "identity"]


@dataclass(frozen=True)
class Hint:
    """An untrusted, uncertified best-effort guess (the H layer).

    H is **outside the privacy contract**: a hint must be projected to the consumer-visible
    set before it is ever surfaced to a human, and it carries NO certificate weight; it
    never enters the certified card set C. No hint producers exist yet; the layer is kept
    structurally separate so certified and uncertified context never share a channel.
    """

    subject: str
    summary: str
    source: str


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
    note: str | None = None
    visibility: str = "silent"
    document_id: str | None = None


@dataclass(frozen=True)
class Coverage:
    """Honest report of what was checked. Absence of cards is never clearance."""

    entries: tuple[CoverageEntry, ...]
    delta: Delta = "none"


Completeness = ClosureStatus


def assess_completeness(prop: Prop, coverage: Coverage) -> Completeness:
    """The paper's ``complete?``: is every mandated dependency of ``prop`` observed fresh?

    Precedence: an absent mandated family is ``incomplete[policy-gap]`` (we never looked). A
    present family whose entries are all ``disabled`` is also ``incomplete[policy-gap]`` (we knew
    the connector exists but did not have the required input). A ``disabled`` source mixed with a
    fresh sibling is ``incomplete[stale-dep]``: one provider in the family was checked, but another
    provider was explicitly not checked, so the family cannot certify clear. Among present,
    non-disabled families the worst status wins: any stale/unavailable/blocked, or any unrecognized
    status, gives ``incomplete[stale-dep]`` (a real unreachable dominates), then ``unbounded`` gives
    ``incomplete[unbounded]``, then ``pending`` gives ``incomplete[pending]``, then a family whose
    only non-fresh status is ``not_applicable`` gives ``not_applicable[out-of-scope]``, else
    ``complete``. Treating an unrecognized status as stale-dep preserves the prior "non-fresh means
    stale-dep" default.
    """

    entries_by_family: dict[str, list[CoverageEntry]] = {}
    for entry in coverage.entries:
        entries_by_family.setdefault(entry.source_family, []).append(entry)

    statuses: list[str] = []
    for family in sorted(deps_for(prop)):
        family_entries = entries_by_family.get(family, [])
        if not family_entries:
            return "incomplete[policy-gap]"
        family_statuses = [entry.status for entry in family_entries]
        if all(status == "disabled" for status in family_statuses):
            return "incomplete[policy-gap]"
        if "disabled" in family_statuses and "fresh" in family_statuses:
            return "incomplete[stale-dep]"
        statuses.extend(family_statuses)

    if any(
        status not in {"fresh", "pending", "not_applicable", "disabled", "unbounded"}
        for status in statuses
    ):
        return "incomplete[stale-dep]"
    if any(status == "unbounded" for status in statuses):
        return "incomplete[unbounded]"
    if any(status == "pending" for status in statuses):
        return "incomplete[pending]"
    if any(status == "not_applicable" for status in statuses):
        return "not_applicable[out-of-scope]"
    return "complete"


def build_coverage(
    statuses: Iterable[SourceStatus],
    delta: Delta = "none",
    *,
    source_documents: Iterable[SourceDocument] = (),
) -> Coverage:
    """Record each observed source's status verbatim, with the declassification dial. The
    dial defaults to ``none``; ``count``/``identity`` declassification of invisible-target
    dangling references is deferred until reference-target tracking exists."""

    document_id_by_source_id = _document_id_by_source_id(source_documents)
    entries = tuple(
        CoverageEntry(
            source_id=status.source_id,
            source_family=status.source_family,
            status=status.status,
            last_checked_at=status.last_checked_at,
            note=status.safe_user_message,
            visibility=status.normal_context_visibility,
            document_id=document_id_by_source_id.get(status.source_id),
        )
        for status in statuses
    )
    return Coverage(entries=entries, delta=delta)


def _document_id_by_source_id(source_documents: Iterable[SourceDocument]) -> dict[str, str]:
    mapping: dict[str, str] = {}
    for document in source_documents:
        for source_id in document.source_ids:
            existing = mapping.get(source_id)
            if existing is not None and existing != document.document_id:
                raise ValueError(f"source id {source_id} belongs to multiple documents")
            mapping[source_id] = document.document_id
    return mapping


def _consumed_document_ids(prop: Prop, coverage: Coverage) -> tuple[str, ...]:
    families = deps_for(prop)
    return tuple(
        sorted(
            {
                entry.document_id
                for entry in coverage.entries
                if entry.source_family in families and entry.document_id is not None
            }
        )
    )


@dataclass(frozen=True)
class ContextSelection:
    """The broker's answer at work-start: rendered cards, the typed certified claims (C), the
    untrusted hint layer (H), honest coverage, per-proposition closure, per-subject authority
    state, and a verifiable-replay digest binding the exact inputs."""

    cards: tuple[ContextCard, ...]
    claim_cards: tuple[ClaimCard, ...]
    hints: tuple[Hint, ...]
    coverage: Coverage
    closure: tuple[ClosureEntry, ...]
    authority: tuple[AuthorityEntry, ...]
    snapshot_digest: str


def select_context(
    request: RequestContext,
    signals: Iterable[SourceSignal],
    statuses: Iterable[SourceStatus],
    declarations: Iterable[AuthorityDecl] = (),
    *,
    source_documents: Iterable[SourceDocument] = (),
) -> ContextSelection:
    """Broker entry point: derive typed claims, render cards, report coverage + closure,
    resolve authority, and bind the inputs with a verifiable-replay digest."""

    signal_list = list(signals)
    status_list = list(statuses)
    declaration_list = list(declarations)
    source_document_list = list(source_documents)
    coverage = build_coverage(status_list, source_documents=source_document_list)
    claim_cards = tuple(derive_claims(request, signal_list))
    cards = tuple(render_claim(claim_card) for claim_card in claim_cards)
    closure = tuple(
        _closure_entry(kind, request, coverage)
        for kind in CARD_KINDS
    )
    subjects = sorted({decl.subject for decl in declaration_list})
    authority = tuple(assess_authority(subject, declaration_list) for subject in subjects)
    # Bind only the P-visible projection of signals: the digest is part of the observable
    # ⟨C, κ⟩, so it must be invariant under P-invisible changes (Theorem 5). Hashing raw
    # signals would let a consumer detect that invisible inputs exist (an existence leak).
    digest = _snapshot_digest(
        request, project_visible_signals(signal_list), status_list, declaration_list
    )
    return ContextSelection(
        cards=cards,
        claim_cards=claim_cards,
        hints=(),
        coverage=coverage,
        closure=closure,
        authority=authority,
        snapshot_digest=digest,
    )


def _closure_entry(kind: CardKind, request: RequestContext, coverage: Coverage) -> ClosureEntry:
    query = kind.query(request)
    return ClosureEntry(
        check_id=kind.check_id,
        proposition=query.predicate,
        consumed_document_ids=_consumed_document_ids(query, coverage),
        closure_status=assess_completeness(query, coverage),
        reason=_closure_reason(kind, request),
    )


def _closure_reason(kind: CardKind, request: RequestContext) -> str:
    query = kind.query(request)
    deps = ", ".join(sorted(deps_for(query)))
    if deps:
        return f"check {kind.check_id} requires source families: {deps}"
    return f"check {kind.check_id} has no source-family dependencies"
