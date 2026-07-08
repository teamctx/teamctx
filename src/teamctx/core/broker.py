"""The broker's single entry point: compose sources, select context, render verdicts.

This module sits at the top of the core import DAG. ``select_context`` lives in
``select`` and ``evaluate`` imports ``select``; the broker needs both, so it must sit
above them, which is exactly why the unified answer cannot live in ``select`` (that would
cycle). Every consumer (CLI, MCP, and the evidence engine) calls ``broker_answer`` so the
verdict logic exists in one place, not re-implemented per transport.

Pure: composition + evaluation only, no I/O (the core purity test guards it).
"""

from __future__ import annotations

from collections.abc import Iterable
from dataclasses import dataclass

from teamctx.core.authority import AuthorityDecl
from teamctx.core.contracts import (
    CoreContractDocument,
    GuidanceRecord,
    RequestContext,
    SourceDocument,
    SourceOpenTarget,
    SourceSignal,
    SourceStatus,
)
from teamctx.core.evaluate import Valuation, evaluate
from teamctx.core.kinds import CARD_KINDS, CheckId, resolve_check_selection
from teamctx.core.select import ContextSelection, select_context


@dataclass(frozen=True)
class ComposedSources:
    """The merged source material from one or more connector documents. Connectors that
    answer the same request each emit a ``CoreContractDocument``; composing them is just the
    union of their signals/statuses/targets/guidance; the broker then selects over the whole."""

    signals: tuple[SourceSignal, ...]
    statuses: tuple[SourceStatus, ...]
    open_targets: tuple[SourceOpenTarget, ...]
    guidance_records: tuple[GuidanceRecord, ...]
    documents: tuple[SourceDocument, ...]


def compose(documents: Iterable[CoreContractDocument]) -> ComposedSources:
    """Merge N connector documents into one set of source material. Order-preserving union;
    no dedup (each connector owns a distinct source, so ids do not collide)."""

    signals: list[SourceSignal] = []
    statuses: list[SourceStatus] = []
    open_targets: list[SourceOpenTarget] = []
    guidance_records: list[GuidanceRecord] = []
    source_documents: list[SourceDocument] = []
    seen_document_ids: set[str] = set()
    for document in documents:
        if document.document_id in seen_document_ids:
            raise ValueError(f"duplicate document id: {document.document_id}")
        seen_document_ids.add(document.document_id)
        source_documents.append(_source_document(document))
        signals.extend(document.source_signals)
        statuses.extend(document.source_statuses)
        open_targets.extend(document.source_open_targets)
        guidance_records.extend(document.guidance_records)
    return ComposedSources(
        signals=tuple(signals),
        statuses=tuple(statuses),
        open_targets=tuple(open_targets),
        guidance_records=tuple(guidance_records),
        documents=tuple(source_documents),
    )


def _source_document(document: CoreContractDocument) -> SourceDocument:
    source_ids = tuple(sorted({status.source_id for status in document.source_statuses}))
    source_families = tuple(
        sorted(
            {status.source_family for status in document.source_statuses}
            | {signal.source_family for signal in document.source_signals}
        )
    )
    return SourceDocument(
        document_id=document.document_id,
        document_type=document.document_type,
        source_ids=source_ids,
        source_families=source_families,
    )


@dataclass(frozen=True)
class BrokerAnswer:
    """The broker's complete answer at work-start: the derived selection (cards, certified
    claims, coverage, closure, authority, replay digest) plus one labeled verdict per card
    kind. ``request`` carries the exact request that produced it. ``verdicts`` is ordered to
    match ``CARD_KINDS``. ``source_signals`` and ``source_statuses`` carry the composed source
    facts for ambient content identity. ``open_targets`` carries every source open target from the
    composed documents, for use by why/open-source commands."""

    request: RequestContext
    selection: ContextSelection
    verdicts: tuple[tuple[str, Valuation], ...]
    source_signals: tuple[SourceSignal, ...] = ()
    source_statuses: tuple[SourceStatus, ...] = ()
    open_targets: tuple[SourceOpenTarget, ...] = ()
    source_documents: tuple[SourceDocument, ...] = ()
    enabled_checks: tuple[CheckId, ...] = ()
    important_checks: tuple[CheckId, ...] = ()
    disabled_checks: tuple[CheckId, ...] = ()


def broker_answer(
    request: RequestContext,
    signals: Iterable[SourceSignal],
    statuses: Iterable[SourceStatus],
    declarations: Iterable[AuthorityDecl] = (),
    *,
    open_targets: Iterable[SourceOpenTarget] = (),
    source_documents: Iterable[SourceDocument] = (),
    enabled_checks: Iterable[CheckId] | None = None,
    important_checks: Iterable[CheckId] | None = None,
    disabled_checks: Iterable[CheckId] | None = None,
) -> BrokerAnswer:
    """The one broker entry point. Derives the selection, then evaluates each card kind's
    universal against the certified claims under the coverage closure, so every consumer
    gets identical cards AND identical verdicts from one code path."""

    signal_tuple = tuple(signals)
    status_tuple = tuple(statuses)
    declaration_tuple = tuple(declarations)
    source_document_tuple = tuple(source_documents)
    check_selection = resolve_check_selection(enabled_checks)
    enabled_tuple = check_selection.enabled_checks
    important_tuple = (
        _ordered_subset(important_checks)
        if important_checks is not None
        else check_selection.important_checks
    )
    disabled_tuple = (
        _ordered_subset(disabled_checks)
        if disabled_checks is not None
        else check_selection.disabled_checks
    )
    selection = select_context(
        request,
        signal_tuple,
        status_tuple,
        declaration_tuple,
        source_documents=source_document_tuple,
        enabled_checks=enabled_tuple,
    )
    verdicts = tuple(
        (
            kind.verdict_label,
            evaluate(kind.query(request), selection.claim_cards, selection.closure),
        )
        for kind in CARD_KINDS
        if kind.check_id in enabled_tuple
    )
    return BrokerAnswer(
        request=request,
        selection=selection,
        verdicts=verdicts,
        source_signals=signal_tuple,
        source_statuses=status_tuple,
        open_targets=tuple(open_targets),
        source_documents=source_document_tuple,
        enabled_checks=enabled_tuple,
        important_checks=important_tuple,
        disabled_checks=disabled_tuple,
    )


def broker_answer_from_documents(
    request: RequestContext,
    documents: Iterable[CoreContractDocument],
    declarations: Iterable[AuthorityDecl] = (),
    *,
    enabled_checks: Iterable[CheckId] | None = None,
    important_checks: Iterable[CheckId] | None = None,
    disabled_checks: Iterable[CheckId] | None = None,
) -> BrokerAnswer:
    """Convenience: compose connector documents, then answer. The unified ``work-start`` and
    the MCP server both run several connectors and hand their documents here."""

    composed = compose(documents)
    return broker_answer(
        request,
        composed.signals,
        composed.statuses,
        declarations,
        open_targets=composed.open_targets,
        source_documents=composed.documents,
        enabled_checks=enabled_checks,
        important_checks=important_checks,
        disabled_checks=disabled_checks,
    )


def _ordered_subset(checks: Iterable[CheckId]) -> tuple[CheckId, ...]:
    allowed = set(checks)
    return tuple(kind.check_id for kind in CARD_KINDS if kind.check_id in allowed)
