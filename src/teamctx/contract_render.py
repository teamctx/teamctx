"""Terminal rendering for Core Contract V0 documents."""

from __future__ import annotations

from collections import OrderedDict
from collections.abc import Iterable

from teamctx.assessment import CheckState, WorkStartAssessment, assess
from teamctx.core.authority import AuthorityEntry
from teamctx.core.broker import BrokerAnswer
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

_HEADLINE = {
    "ready": "Looks clear to start.",
    "heads_up": "Before you start, here is what to handle first:",
    "cant_verify": "Heads up: I couldn't check the important things:",
}
_CLEAR_PHRASE = {
    "conflict": "no open PRs touch your files",
    "gate": "CI is green",
    "docs": "the docs you rely on are current",
    "criteria": "the linked issue's criteria are unchanged",
}
_NOT_CHECKED_PHRASE = {
    "criteria": "spec changes (no issue is linked to this branch; link one to enable)",
    "docs": "docs (no docs root is configured; set work_start.docs_root to enable)",
    "gate": "failing checks (couldn't determine your branch)",
    "conflict": "open PRs (couldn't determine the repository)",
}
_UNREACHABLE_PHRASE = {
    "conflict": "open PRs (couldn't reach GitHub)",
    "gate": "failing checks (couldn't reach GitHub)",
    "criteria": "spec changes (couldn't reach GitHub)",
    "docs": "the docs you rely on (couldn't read the docs folder)",
}
_FINDING_ACTION = {
    "conflict": "look at it before you edit so you don't undo each other's work",
    "criteria": "re-check the criteria before you rely on them",
    "docs": "rely on the current one instead",
    "gate": "fix it or wait for a green build before relying on it",
}


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


def _authority_line(entry: AuthorityEntry) -> str:
    if entry.state == "resolved":
        return f"- {entry.subject}: resolved (value {entry.value})"
    if entry.state == "conflicted":
        return f"- {entry.subject}: CONFLICTED: declared sources disagree; not adjudicated"
    if entry.state == "unknown[stale-authority]":
        return f"- {entry.subject}: unknown: declared authority is stale; refresh it"
    return f"- {entry.subject}: no authority declared"


def render_broker_answer(answer: BrokerAnswer) -> str:
    """The one render every transport uses: a signal-led plain-prose report of the broker's
    answer. Decision-enabling; gaps carry their reason and how to turn them on. Deterministic,
    never via an LLM, and prints: it never blocks."""

    assessment = assess(answer)
    lines = [_HEADLINE[assessment.kind]]
    lines.extend(_finding_bullets(assessment))
    coverage = _coverage_line(assessment)
    if coverage:
        lines.append(coverage)
    couldnt = _couldnt_check_line(assessment)
    if couldnt:
        lines.append(couldnt)
    not_checked = _not_checked_line(assessment)
    if not_checked:
        lines.append(not_checked)
    lines.extend(_authority_block(answer.selection))
    return "\n".join(lines) + "\n"


def _finding_bullets(assessment: WorkStartAssessment) -> list[str]:
    if assessment.kind == "heads_up":
        bullets: list[str] = []
        for state in assessment.checks:
            if state.status == "found":
                bullets.extend(f"  • {_finding_text(state, card)}" for card in state.cards)
        return bullets
    if assessment.kind == "cant_verify":
        return _cant_verify_bullets(assessment)
    return []


def _finding_text(state: CheckState, card: ContextCard) -> str:
    action = _FINDING_ACTION.get(state.check, "")
    pr = _gh_hint(card.source_display)
    base = f"{card.text}: {action}" if action else card.text
    return f"{base}{pr}"


def _gh_hint(source_display: str) -> str:
    marker = source_display.rfind("#")
    if marker == -1:
        return ""
    digits = ""
    for ch in source_display[marker + 1:]:
        if ch.isdigit():
            digits += ch
        else:
            break
    return f" (gh pr view {digits})" if digits else ""


def _cant_verify_bullets(assessment: WorkStartAssessment) -> list[str]:
    status = {s.check: s.status for s in assessment.checks}
    conflict = status.get("conflict") == "unreachable"
    gate = status.get("gate") == "unreachable"
    fix = (
        "teamctx couldn't reach GitHub. Either it has no access yet (run `teamctx install-hook` "
        "to connect it) or it's a temporary connection issue."
    )
    if conflict and gate:
        return [f"  • Open PRs and failing checks: {fix} Until it's back you won't see colliding "
                "PRs or red CI on your files."]
    if conflict:
        return [f"  • Open PRs: {fix} Until it's back you won't see colliding PRs on your files."]
    if gate:
        return [f"  • Failing checks: {fix} Until it's back you won't see red CI on your files."]
    return []


def _coverage_line(assessment: WorkStartAssessment) -> str:
    clear = [_CLEAR_PHRASE[s.check] for s in assessment.checks if s.status == "clear"]
    if not clear:
        return ""
    label = "Checked: " if assessment.kind == "ready" else "Also checked: "
    return "  " + label + "; ".join(clear) + "."


def _couldnt_check_line(assessment: WorkStartAssessment) -> str:
    # Surface every unreachable check that isn't already in the can't-verify bullets. Those
    # bullets only fire when kind == cant_verify and only for the important checks, so in any
    # other mode (a found check made it heads_up) the unreachable important checks must be
    # surfaced here too. Honest-UNKNOWN is never silently dropped.
    in_bullets = assessment.kind == "cant_verify"
    gaps = [
        _UNREACHABLE_PHRASE[s.check]
        for s in assessment.checks
        if s.status == "unreachable"
        and not (in_bullets and s.check in ("conflict", "gate"))
    ]
    if not gaps:
        return ""
    return "  Couldn't check: " + "; ".join(gaps) + "."


def _not_checked_line(assessment: WorkStartAssessment) -> str:
    gaps = [_NOT_CHECKED_PHRASE[s.check] for s in assessment.checks if s.status == "not_configured"]
    if not gaps:
        return ""
    return "  Not checked: " + "; ".join(gaps) + "."


def _authority_block(selection: ContextSelection) -> list[str]:
    if not selection.authority:
        return []
    lines = ["", "Authority"]
    lines.extend(_authority_line(entry) for entry in selection.authority)
    return lines


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
