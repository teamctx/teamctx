"""The one card-kind registry: every fact about a card kind lives on its ``CardKind`` entry.

A card kind is a whole vertical: which source signal it derives from, the typed proposition it
asserts (an existential) and the universal that proposition refutes, how it renders to a human,
and the cost, dependency, and routing facts the rest of the broker needs. This module OWNS that
registry (``CARD_KINDS``) and DERIVES every lookup the engine, evaluator, severity, and
assessment used to keep as separate hand-written tables: predicate shapes, refutes pairs,
dependency closures, severity bases, verdict-to-check pairs, and reason-prefix routing. Adding a
kind is a single ``CardKind`` entry; no other table needs a new row.

Dependency direction (no cycles, one definition site per fact): this module imports the pure
datatypes and mechanisms (contracts, prop, severity) only. The engine (select), the evaluator
(evaluate), the broker, and assessment import this module; this module imports none of them.

Pure: dataclasses, typing, and internal core imports only (the core purity test guards this).
"""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass
from typing import Literal

from teamctx.core.contracts import (
    ContextCard,
    RequestContext,
    SectionName,
    SourceSignal,
)
from teamctx.core.prop import Prop, PropShape, RefutesMatch, SubjectRef, Witness, witnesses_with
from teamctx.core.severity import compute_severity

CheckId = Literal["conflict", "criteria", "docs", "gate"]


@dataclass(frozen=True)
class ClaimCard:
    """A derived typed claim paired with the source signal it was derived from.

    ``claim`` is the proposition the card asserts (and witnesses); ``signal`` carries the
    render inputs. The render card is a pure function of this pair (each kind's renderer).
    """

    claim: Prop
    signal: SourceSignal


# --- the four kinds' query propositions: the universal each kind's card refutes ---


def no_conflict_query(request: RequestContext) -> Prop:
    """The universal a collision card refutes: 'no open PR conflicts with my paths'."""

    return Prop(
        predicate="no_pr_conflicts_with_paths",
        subject=SubjectRef(repo=request.repo, paths=tuple(request.paths)),
    )


def criteria_changed_query(request: RequestContext) -> Prop:
    """The universal a criteria-changed card refutes: 'no acceptance criteria changed for
    my linked issues'."""

    return Prop(
        predicate="no_criteria_changed_for_issues",
        subject=SubjectRef(repo=request.repo, paths=tuple(request.linked_issues)),
    )


def no_superseded_docs_query(request: RequestContext) -> Prop:
    """The universal a doc-superseded card refutes: 'no doc I rely on was superseded'."""

    return Prop(
        predicate="no_superseded_docs",
        subject=SubjectRef(repo=request.repo, paths=tuple(request.paths)),
    )


def all_gates_pass_query(request: RequestContext) -> Prop:
    """The universal a missed-gate card refutes: 'all gates pass for my change'."""

    return Prop(
        predicate="all_gates_pass",
        subject=SubjectRef(repo=request.repo, paths=tuple(request.paths)),
    )


# --- the four kinds' derive functions: a P-visible signal + request -> a typed claim or None ---


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


def _derive_criteria_changed_claim(
    request: RequestContext, signal: SourceSignal
) -> ClaimCard | None:
    issue = signal.scope.get("issue")
    if not isinstance(issue, str) or issue not in request.linked_issues:
        return None
    claim = Prop(
        predicate="issue_criteria_changed",
        subject=SubjectRef(repo=request.repo, paths=(issue,)),
        args=(signal.id,),
    )
    return ClaimCard(claim=claim, signal=signal)


def _derive_doc_superseded_claim(
    request: RequestContext, signal: SourceSignal
) -> ClaimCard | None:
    if signal.scope.get("repo") != request.repo:
        return None
    doc = signal.scope.get("doc")
    if not isinstance(doc, str):
        return None
    claim = Prop(
        predicate="doc_superseded",
        subject=SubjectRef(repo=request.repo, paths=(doc,)),
        args=(signal.id,),
    )
    return ClaimCard(claim=claim, signal=signal)


def _derive_missed_gate_claim(
    request: RequestContext, signal: SourceSignal
) -> ClaimCard | None:
    if signal.scope.get("repo") != request.repo:
        return None
    gate = signal.scope.get("gate")
    if not isinstance(gate, str) or not gate:
        return None
    claim = Prop(
        predicate="gate_failed",
        subject=SubjectRef(repo=request.repo, paths=(gate,)),
        args=(signal.id,),
    )
    return ClaimCard(claim=claim, signal=signal)


# --- rendering: the shared skeleton, then one renderer per kind ---


def _render_claim_card(
    claim_card: ClaimCard,
    *,
    section: SectionName,
    why_this_matters: str,
    reason: str,
    reason_code: str,
) -> ContextCard:
    """The shared render skeleton. Every kind's card differs only in section, why, reason,
    and reason_code; the rest (status-only body, verify-before-relying, severity) is uniform."""

    claim = claim_card.claim
    signal = claim_card.signal
    return ContextCard(
        schema_version="teamctx.context_card.v0",
        id=f"card_{signal.id}",
        section=section,
        text=signal.evidence_summary,
        why_this_matters=why_this_matters,
        source_display=signal.source_display,
        refs=[signal.id],
        reason=reason,
        scope=dict(signal.scope),
        freshness=signal.freshness,
        confidence=signal.confidence,
        source_body="status_only",
        source_open_target_id=None,
        agent_instruction="verify_before_relying",
        reason_code=reason_code,
        severity=compute_severity(severity_base_for(claim.predicate), claim),
    )


def render_collision_claim(claim_card: ClaimCard) -> ContextCard:
    """Render a collision claim into a human-plane ``ContextCard``.

    Pure: the render card is a function of the claim plus its signal. Output matches the
    pre-typed collision derivation byte for byte.
    """

    claim = claim_card.claim
    overlap = ", ".join(claim.subject.paths)
    return _render_claim_card(
        claim_card,
        section="Needs attention",
        why_this_matters=f"you are editing {claim.subject.paths[0]}.",  # most-salient path
        reason=f"same repository and file path as the current task: {overlap}",
        reason_code="collision.same_path",
    )


def render_criteria_changed_claim(claim_card: ClaimCard) -> ContextCard:
    """Render a criteria-changed claim into a human-plane ``ContextCard``."""

    issue = claim_card.claim.subject.paths[0]
    return _render_claim_card(
        claim_card,
        section="Verify before relying",
        why_this_matters=f"acceptance criteria for {issue} changed; re-check before relying.",
        reason=f"linked issue {issue} had its acceptance criteria changed",
        reason_code="criteria.changed",
    )


def render_doc_superseded_claim(claim_card: ClaimCard) -> ContextCard:
    """Render a doc-superseded claim into a human-plane ``ContextCard``.

    Names the superseding doc when the signal carries ``scope["superseded_by"]`` (so the card
    says WHAT to open, not only THAT the doc is stale); falls back byte-for-byte otherwise."""

    claim = claim_card.claim
    signal = claim_card.signal
    doc = claim.subject.paths[0]
    superseded_by = signal.scope.get("superseded_by")
    current = superseded_by if isinstance(superseded_by, str) and superseded_by else None
    if current is not None:
        why = f"{doc} was superseded; rely on {current} instead, not {doc}."
        reason = f"the doc {doc} was superseded by {current}"
    else:
        why = f"the doc {doc} was superseded; verify it is current before relying."
        reason = f"a doc you rely on ({doc}) was superseded"
    return _render_claim_card(
        claim_card,
        section="Verify before relying",
        why_this_matters=why,
        reason=reason,
        reason_code="doc.superseded",
    )


def render_missed_gate_claim(claim_card: ClaimCard) -> ContextCard:
    """Render a missed-gate claim into a human-plane ``ContextCard``."""

    gate = claim_card.claim.subject.paths[0]
    return _render_claim_card(
        claim_card,
        section="Needs attention",
        why_this_matters=f"a check is failing on this branch: {gate}.",
        reason=f"a check is failing on this branch: {gate}",
        reason_code="gate.failed",
    )


@dataclass(frozen=True)
class CardKind:
    """One registered card kind: every fact about it in one place. ``signal_type`` is the source
    signal it derives from; ``card_predicate``/``query_predicate`` are the existential it asserts
    and the universal that refutes; ``verdict_label``/``check_id``/``reason_prefix`` route it into
    the assessment; ``deps_family`` is the source family its truth depends on; ``severity_base``
    is its cost-of-not-knowing base; ``refutes_match`` is the structural overlap a refutation
    needs; ``derive``/``query``/``render`` are its behavior. New kinds are added by appending an
    entry; the engine's control flow and every derived table follow automatically."""

    signal_type: str
    card_predicate: str  # existential
    query_predicate: str  # universal
    verdict_label: str
    check_id: CheckId
    reason_prefix: str  # "collision" | "criteria" | "doc" | "gate" (assessment routing)
    deps_family: str
    severity_base: float
    refutes_match: RefutesMatch
    derive: Callable[[RequestContext, SourceSignal], ClaimCard | None]
    query: Callable[[RequestContext], Prop]
    render: Callable[[ClaimCard], ContextCard]


CARD_KINDS: tuple[CardKind, ...] = (
    CardKind(
        signal_type="collision",
        card_predicate="pr_conflicts_with_path",
        query_predicate="no_pr_conflicts_with_paths",
        verdict_label="Conflict check",
        check_id="conflict",
        reason_prefix="collision",
        deps_family="git_hosting",
        severity_base=0.8,
        refutes_match="subject-overlap",
        derive=_derive_collision_claim,
        query=no_conflict_query,
        render=render_collision_claim,
    ),
    CardKind(
        signal_type="criteria_changed",
        card_predicate="issue_criteria_changed",
        query_predicate="no_criteria_changed_for_issues",
        verdict_label="Criteria check",
        check_id="criteria",
        reason_prefix="criteria",
        deps_family="issue_tracker",
        severity_base=0.5,
        refutes_match="subject-overlap",
        derive=_derive_criteria_changed_claim,
        query=criteria_changed_query,
        render=render_criteria_changed_claim,
    ),
    CardKind(
        signal_type="doc_superseded",
        card_predicate="doc_superseded",
        query_predicate="no_superseded_docs",
        verdict_label="Docs check",
        check_id="docs",
        reason_prefix="doc",
        deps_family="docs",
        severity_base=0.4,
        refutes_match="repo-wide",
        derive=_derive_doc_superseded_claim,
        query=no_superseded_docs_query,
        render=render_doc_superseded_claim,
    ),
    CardKind(
        signal_type="missed_gate",
        card_predicate="gate_failed",
        query_predicate="all_gates_pass",
        verdict_label="Gate check",
        check_id="gate",
        reason_prefix="gate",
        deps_family="ci_deploy",
        severity_base=0.7,
        refutes_match="repo-wide",
        derive=_derive_missed_gate_claim,
        query=all_gates_pass_query,
        render=render_missed_gate_claim,
    ),
)


# --- derived lookups: one definition site (CARD_KINDS); everything else reads these ---


def _build_predicate_registry() -> dict[str, PropShape]:
    """The predicates this build models and their logical shape, derived from the kinds. A
    universal ('no PR conflicts with any of my paths') is refuted by a single counterexample; an
    existential ('a PR conflicts with this path') is witnessed by a single instance."""

    registry: dict[str, PropShape] = {}
    for kind in CARD_KINDS:
        registry[kind.card_predicate] = "existential"
        registry[kind.query_predicate] = "universal"
    return registry


# The predicate shapes (8 entries: one existential + one universal per kind).
PREDICATE_REGISTRY: dict[str, PropShape] = _build_predicate_registry()

# Each pair is (card_predicate, query_predicate) mapped to the structural overlap a refutation
# requires: a card asserting card_predicate REFUTES the universal query_predicate under that
# match rule. Collision and criteria use subject-overlap (shared repo + at least one shared
# item). Docs and gate use repo-wide (shared repo alone): reliance is the whole declared docs
# set, and gate status is branch-scoped rather than file-scoped.
_REFUTES_MATCH: dict[tuple[str, str], RefutesMatch] = {
    (kind.card_predicate, kind.query_predicate): kind.refutes_match for kind in CARD_KINDS
}
REFUTES_PAIRS: frozenset[tuple[str, str]] = frozenset(_REFUTES_MATCH)

# Placeholder bases per card predicate (cost-of-not-knowing). Calibration deferred.
KIND_BASE: dict[str, float] = {kind.card_predicate: kind.severity_base for kind in CARD_KINDS}

# deps_G: the trusted, mandated source families a proposition's truth depends on. An
# unregistered predicate fails loud; we never silently certify a query whose dependencies we
# have not modeled.
DEPS_REGISTRY: dict[str, frozenset[str]] = {
    kind.query_predicate: frozenset({kind.deps_family}) for kind in CARD_KINDS
}

# The (verdict_label, check_id) pairs the assessment consumes to route each verdict to its check.
LABEL_CHECK_PAIRS: tuple[tuple[str, CheckId], ...] = tuple(
    (kind.verdict_label, kind.check_id) for kind in CARD_KINDS
)

# reason_prefix (the head of a card's reason_code, before the dot) -> the check it belongs to.
REASON_PREFIX: dict[str, CheckId] = {kind.reason_prefix: kind.check_id for kind in CARD_KINDS}

# check -> mandated source family, used by assessment to route disabled-source notes.
CHECK_DEPS_FAMILY: dict[CheckId, str] = {
    kind.check_id: kind.deps_family for kind in CARD_KINDS
}


def shape_of(prop: Prop) -> PropShape:
    """The logical shape of a proposition's predicate. Raises on an unregistered predicate."""

    try:
        return PREDICATE_REGISTRY[prop.predicate]
    except KeyError as exc:
        raise ValueError(f"unregistered predicate: {prop.predicate!r}") from exc


def witnesses(claim: Prop, query: Prop) -> Witness:
    """Does a card's ``claim`` witness ``query`` (supports), its negation (refutes), or
    neither (unrelated)? Deterministic over typed structure only.

    A registered ``(claim.predicate, query.predicate)`` refutes-pair, satisfied under that pair's
    match rule (subject-overlap or repo-wide), refutes the (universal) query. ``supports`` is
    reserved for kinds whose claim establishes a query directly.
    """

    match = _REFUTES_MATCH.get((claim.predicate, query.predicate))
    if match is None:
        return "unrelated"
    return witnesses_with(claim, query, match)


def deps_for(prop: Prop) -> frozenset[str]:
    """The mandated source families whose state can affect ``prop`` (deps_G)."""

    try:
        return DEPS_REGISTRY[prop.predicate]
    except KeyError as exc:
        raise ValueError(
            f"no dependency closure registered for predicate {prop.predicate!r}"
        ) from exc


def severity_base_for(predicate: str) -> float:
    """The cost-of-not-knowing base for a card predicate. Raises on an unregistered predicate."""

    try:
        return KIND_BASE[predicate]
    except KeyError as exc:
        raise ValueError(f"no severity base registered for predicate {predicate!r}") from exc
