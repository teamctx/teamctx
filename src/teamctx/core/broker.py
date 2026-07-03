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
    SourceOpenTarget,
    SourceSignal,
    SourceStatus,
)
from teamctx.core.evaluate import Valuation, evaluate
from teamctx.core.kinds import CARD_KINDS
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


def compose(documents: Iterable[CoreContractDocument]) -> ComposedSources:
    """Merge N connector documents into one set of source material. Order-preserving union;
    no dedup (each connector owns a distinct source, so ids do not collide)."""

    signals: list[SourceSignal] = []
    statuses: list[SourceStatus] = []
    open_targets: list[SourceOpenTarget] = []
    guidance_records: list[GuidanceRecord] = []
    for document in documents:
        signals.extend(document.source_signals)
        statuses.extend(document.source_statuses)
        open_targets.extend(document.source_open_targets)
        guidance_records.extend(document.guidance_records)
    return ComposedSources(
        signals=tuple(signals),
        statuses=tuple(statuses),
        open_targets=tuple(open_targets),
        guidance_records=tuple(guidance_records),
    )


@dataclass(frozen=True)
class BrokerAnswer:
    """The broker's complete answer at work-start: the derived selection (cards, certified
    claims, coverage, closure, authority, replay digest) plus one labeled verdict per card
    kind. ``verdicts`` is ordered to match ``CARD_KINDS``. ``open_targets`` carries every
    source open target from the composed documents, for use by why/open-source commands."""

    selection: ContextSelection
    verdicts: tuple[tuple[str, Valuation], ...]
    open_targets: tuple[SourceOpenTarget, ...] = ()


def broker_answer(
    request: RequestContext,
    signals: Iterable[SourceSignal],
    statuses: Iterable[SourceStatus],
    declarations: Iterable[AuthorityDecl] = (),
    *,
    open_targets: Iterable[SourceOpenTarget] = (),
) -> BrokerAnswer:
    """The one broker entry point. Derives the selection, then evaluates each card kind's
    universal against the certified claims under the coverage closure, so every consumer
    gets identical cards AND identical verdicts from one code path."""

    selection = select_context(request, signals, statuses, declarations)
    verdicts = tuple(
        (
            kind.verdict_label,
            evaluate(kind.query(request), selection.claim_cards, selection.closure),
        )
        for kind in CARD_KINDS
    )
    return BrokerAnswer(selection=selection, verdicts=verdicts, open_targets=tuple(open_targets))


def broker_answer_from_documents(
    request: RequestContext,
    documents: Iterable[CoreContractDocument],
    declarations: Iterable[AuthorityDecl] = (),
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
    )
