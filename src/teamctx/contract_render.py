"""Terminal rendering for Core Contract V0 documents."""

from __future__ import annotations

from collections import OrderedDict
from collections.abc import Iterable

from teamctx.core.contracts import (
    ContextCard,
    CoreContractDocument,
    Scope,
    SourceOpenTarget,
    SourceStatus,
)
from teamctx.core.select import ContextSelection

SECTION_ORDER = (
    "Needs attention",
    "Project guidance",
    "Verify before relying",
    "Source unavailable",
    "Good to know",
)


def render_contract_context(document: CoreContractDocument) -> str:
    grouped: OrderedDict[str, list[ContextCard]] = OrderedDict()
    for card in sort_contract_cards(document.context_cards):
        grouped.setdefault(card.section, []).append(card)

    lines = ["Working context"]
    if not grouped:
        lines.extend(["", "No working context for this task."])
    else:
        for section, section_cards in grouped.items():
            lines.extend(["", section])
            for card in section_cards:
                lines.append(f"- {card.text}")
                lines.append(f"  Why this matters: {card.why_this_matters}")
                lines.append(f"  Source: {card.source_display}")

    visible_statuses = source_statuses_for_terminal(document.source_statuses)
    if visible_statuses:
        lines.extend(["", "Source status"])
        for status in visible_statuses:
            lines.append(f"- {status.safe_user_message}")
            lines.append(f"  Source: {source_status_label(status)}")

    return "\n".join(lines) + "\n"


def render_selection(selection: ContextSelection) -> str:
    """Human-plane render of the broker's answer: derived cards + honest coverage."""

    grouped: OrderedDict[str, list[ContextCard]] = OrderedDict()
    for card in sort_contract_cards(selection.cards):
        grouped.setdefault(card.section, []).append(card)

    lines = ["Working context"]
    if not grouped:
        lines.extend(["", "No working context for this task."])
    else:
        for section, section_cards in grouped.items():
            lines.extend(["", section])
            for card in section_cards:
                lines.append(f"- {card.text}")
                lines.append(f"  Why this matters: {card.why_this_matters}")
                lines.append(f"  Source: {card.source_display}")

    lines.extend(["", "Coverage"])
    coverage = selection.coverage
    if not coverage.entries:
        lines.append("- no sources were checked")
    for entry in coverage.entries:
        lines.append(f"- {entry.source_family}: {entry.status}")
    if coverage.complete:
        lines.append("Coverage complete across checked sources.")
    else:
        lines.append(
            "Absence of a card is not an all-clear; "
            "treat unobserved or stale sources as Unknown."
        )

    return "\n".join(lines) + "\n"


def render_contract_why(document: CoreContractDocument, card_id: str) -> str:
    card = find_contract_card(document, card_id)
    return (
        "Show why\n\n"
        f"This appears because {card.reason}.\n\n"
        f"Source: {card.source_display}\n"
        f"Freshness: {card.freshness}\n"
        f"Scope: {scope_label(card.scope)}\n"
        f"Confidence: {card.confidence}\n"
        f"Source body: {source_body_label(card)}\n"
        f"Agent visibility: {agent_visibility_label(card)}\n"
    )


def render_contract_open_source(document: CoreContractDocument, ref_id: str) -> str:
    target = find_contract_open_target(document, ref_id)
    lines = [target.open_label, "", target.source_display]
    if target.body_availability == "available":
        lines.extend(
            [
                "",
                "Source body available by explicit provider action.",
                "TeamCtx did not store source text in this context document.",
            ]
        )
        return "\n".join(lines) + "\n"

    lines.extend(
        ["", "Source body unavailable.", f"Reason: {source_open_reason(target.body_availability)}"]
    )
    return "\n".join(lines) + "\n"


def find_contract_open_target(document: CoreContractDocument, ref_id: str) -> SourceOpenTarget:
    for target in document.source_open_targets:
        if target.id == ref_id:
            return target

    try:
        card = find_contract_card(document, ref_id)
    except KeyError:
        card = None
    if card is not None and card.source_open_target_id is not None:
        for target in document.source_open_targets:
            if target.id == card.source_open_target_id:
                return target

    raise KeyError(ref_id)


def find_contract_card(document: CoreContractDocument, card_id: str) -> ContextCard:
    for card in document.context_cards:
        if card.id == card_id:
            return card
    raise KeyError(card_id)


def sort_contract_cards(cards: Iterable[ContextCard]) -> list[ContextCard]:
    section_rank = {section: index for index, section in enumerate(SECTION_ORDER)}
    return sorted(cards, key=lambda card: section_rank.get(card.section, len(section_rank)))


def source_statuses_for_terminal(statuses: Iterable[SourceStatus]) -> list[SourceStatus]:
    return [
        status
        for status in statuses
        if status.normal_context_visibility != "silent" and status.status != "fresh"
    ]


def source_status_label(status: SourceStatus) -> str:
    provider = status.scope.get("provider")
    repo = status.scope.get("repo")
    if isinstance(provider, str) and isinstance(repo, str):
        return f"{provider_label(provider)} {repo}"
    return status.source_id


def scope_label(scope: Scope) -> str:
    parts: list[str] = []
    repo = scope.get("repo")
    service = scope.get("service")
    files = scope.get("files")
    if isinstance(repo, str):
        parts.append(repo)
    if isinstance(service, str):
        parts.append(service)
    if isinstance(files, list):
        parts.extend(files)
    return ", ".join(parts) if parts else "current task"


def source_body_label(card: ContextCard) -> str:
    if card.source_body == "openable":
        return "available only by explicit source-open action"
    if card.source_body == "status_only":
        return "not shown; only status and allowed metadata are available"
    if card.source_body == "blocked":
        return "blocked by policy"
    if card.source_body == "unavailable":
        return "unavailable with current access"
    return "not collected"


def agent_visibility_label(card: ContextCard) -> str:
    if card.agent_instruction == "apply_when_in_scope":
        return "shown as scoped guidance"
    if card.agent_instruction == "verify_before_relying":
        return "shown as evidence to verify before relying"
    return "shown as evidence, not instruction"


def provider_label(provider: str) -> str:
    if provider == "github":
        return "GitHub"
    if provider == "gitlab":
        return "GitLab"
    return provider


def source_open_reason(body_availability: str) -> str:
    if body_availability == "status_only":
        return "TeamCtx has allowed metadata for this source, but not source body text."
    if body_availability == "blocked":
        return "This source is blocked by policy."
    if body_availability == "unavailable":
        return "This source is unavailable with current access."
    return "No source body was collected for this source."
