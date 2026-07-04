"""Terminal rendering for Core Contract V0 documents."""

from __future__ import annotations

from dataclasses import dataclass
from typing import cast

from teamctx.ambient import Delta, FindingMaterial
from teamctx.assessment import (
    IMPORTANT_CHECKS,
    CheckState,
    WorkStartAssessment,
    assess,
    card_finding_key,
)
from teamctx.core.authority import AuthorityEntry
from teamctx.core.broker import BrokerAnswer
from teamctx.core.contracts import (
    ContextCard,
    SourceOpenTarget,
)
from teamctx.core.kinds import CARD_KINDS, REASON_PREFIX, CheckId
from teamctx.core.select import ContextSelection

_HEADLINE = {
    "ready": "Looks clear to start.",
    "heads_up": "Before you start, here is what to handle first:",
    "cant_verify": "Heads up: I can't confirm the important things yet:",
}
@dataclass(frozen=True)
class CheckCopy:
    """The per-check human copy at the render edge, one entry per check. Voice stays
    hand-written (owned by the CTO); consolidating it into one struct means a new card kind
    cannot silently ship without the phrases the report and the hook need. ``hook_gap`` is None
    for a low-stakes check (one that is never headlined as an unconfirmed important gap)."""

    clear: str  # the checked-and-clear coverage phrase
    not_checked: str  # the not-configured "Not checked" phrase
    unreachable: str  # the "Couldn't check" phrase
    finding_action: str  # what to do about a finding, appended to the finding text
    hook_clear: str  # the glanceable hook's checked-and-clear phrase
    hook_gap: str | None  # the glanceable hook's unconfirmed-gap phrase (None = not important)
    gitlab_clear: str | None = None
    gitlab_unreachable: str | None = None
    gitlab_hook_clear: str | None = None
    gitlab_hook_gap: str | None = None


# One definition site for every check's copy. The completeness check below fails loud at import
# if a card kind lacks an entry, so a new kind never silently drops from the report.
RENDER_COPY: dict[CheckId, CheckCopy] = {
    "conflict": CheckCopy(
        clear="no other open PRs touch your files",
        not_checked="open PRs (couldn't determine the repository)",
        unreachable="open PRs (couldn't reach GitHub)",
        finding_action="look at it before you edit so you don't undo each other's work",
        hook_clear="no other open pull requests touch these files",
        hook_gap="open pull requests",
        gitlab_clear="no other open MRs touch your files",
        gitlab_unreachable="open MRs (couldn't reach GitLab)",
        gitlab_hook_clear="no other open merge requests touch these files",
        gitlab_hook_gap="open merge requests",
    ),
    "criteria": CheckCopy(
        clear="the linked issue's criteria are unchanged",
        not_checked="spec changes (no issue is linked to this branch; link one to enable)",
        unreachable="spec changes (couldn't reach GitHub)",
        finding_action="re-check the criteria before you rely on them",
        hook_clear="the linked issue's criteria are unchanged",
        hook_gap=None,
    ),
    "docs": CheckCopy(
        clear="the docs you rely on are current",
        not_checked="docs (no docs root is configured; set work_start.docs_root to enable)",
        unreachable="the docs you rely on (couldn't read the docs folder)",
        finding_action="rely on the current one instead",
        hook_clear="the docs you rely on are current",
        hook_gap=None,
    ),
    "gate": CheckCopy(
        clear="no failing checks found",
        not_checked="failing checks (couldn't determine your branch)",
        unreachable="failing checks (couldn't reach GitHub)",
        finding_action="fix it or wait for a green build before relying on it",
        hook_clear="no failing checks found",
        hook_gap="failing checks",
        gitlab_unreachable="pipeline state (couldn't reach GitLab)",
        gitlab_hook_gap="pipeline state",
    ),
}

if set(RENDER_COPY) != {kind.check_id for kind in CARD_KINDS}:
    raise RuntimeError(
        "RENDER_COPY must carry exactly one entry per card kind; "
        f"have {sorted(RENDER_COPY)}, need {sorted(kind.check_id for kind in CARD_KINDS)}"
    )

_PENDING_PHRASE: dict[CheckId, str] = {
    "gate": "failing checks (CI still running, not confirmed green yet)",
}
# No check emits not_applicable today (docs stopped: reliance is the whole declared docs set).
# The generic fallback below keeps the render path honest for any future kind that does.
_NOT_APPLICABLE_PHRASE: dict[CheckId, str] = {}


def _pending_phrase(check: CheckId) -> str:
    return _PENDING_PHRASE.get(check, f"{check} (still running, not confirmed yet)")


def _not_applicable_phrase(check: CheckId) -> str:
    return _NOT_APPLICABLE_PHRASE.get(check, f"{check} (not applicable to the files in scope)")


def _pending_bullet(check: CheckId) -> str:
    if check == "gate":
        return (
            "  • Failing checks: CI checks are still running, so the gate isn't confirmed "
            "green yet. Wait for the build or check the run before relying on a green gate."
        )
    return f"  • {check}: still running, not confirmed yet."


def check_clear_copy(check: CheckId, forge: str) -> str:
    copy = RENDER_COPY[check]
    if forge == "gitlab" and copy.gitlab_clear is not None:
        return copy.gitlab_clear
    return copy.clear


def check_unreachable_copy(check: CheckId, forge: str) -> str:
    copy = RENDER_COPY[check]
    if forge == "gitlab" and copy.gitlab_unreachable is not None:
        return copy.gitlab_unreachable
    return copy.unreachable


def check_hook_clear_copy(check: CheckId, forge: str) -> str:
    copy = RENDER_COPY[check]
    if forge == "gitlab" and copy.gitlab_hook_clear is not None:
        return copy.gitlab_hook_clear
    return copy.hook_clear


def check_hook_gap_copy(check: CheckId, forge: str) -> str | None:
    copy = RENDER_COPY[check]
    if forge == "gitlab" and copy.gitlab_hook_gap is not None:
        return copy.gitlab_hook_gap
    return copy.hook_gap


# --- the delta lane: what changed since work start, spoken first and once, in one voice ---
# The CTO owns every string here; each maps a delta direction+check to its pinned "since you
# started: ..." line. The delta lane is transport-agnostic: the hook signal and the full report
# both prepend these, so a mid-session change reads identically in either surface.


def delta_lines(
    deltas: tuple[Delta, ...], checks: tuple[CheckState, ...], forge: str
) -> list[str]:
    """The pinned delta lines, one per delta, in delta order. Empty when nothing changed, so the
    CLI/MCP report and the quiet hook are byte-for-byte unchanged with no delta document."""

    return [_delta_line(delta, checks, forge) for delta in deltas]


def _delta_line(delta: Delta, checks: tuple[CheckState, ...], forge: str) -> str:
    if delta.direction == "appear":
        return "since you started: " + _appear_body(delta.check, delta.identity)
    if delta.direction == "disappear":
        return "since you started: " + _disappear_body(delta.check, delta.identity)
    if delta.direction == "transition":
        return f"{_source_name(forge)} is back: " + _recovery_tail(delta.check, checks, forge)
    phrase = check_hook_gap_copy(_as_check(delta.check), forge) or delta.check
    note = delta.note or _shrank_default_note(delta.check, forge)
    return f"since you started: {phrase} can no longer be verified ({note})"


def _appear_body(check: str, identity: FindingMaterial) -> str:
    if check == "conflict":
        return f"{identity.source_display} appeared, touching {', '.join(identity.paths)}"
    if check == "gate":
        return f"check '{identity.gate}' started failing on this branch"
    if check == "criteria":
        return f"{identity.source_display} changed: {identity.detail}"
    if identity.superseded_by:
        return f"{identity.doc} was superseded by {identity.superseded_by}"
    return f"{identity.doc} was superseded"


def _disappear_body(check: str, identity: FindingMaterial) -> str:
    if check == "conflict":
        return f"{identity.source_display} no longer touches your files"
    if check == "gate":
        return f"check '{identity.gate}' is green again"
    if check == "criteria":
        return f"{identity.source_display} is no longer flagged"
    return f"the note about {identity.doc} cleared"


def _recovery_tail(check: str, checks: tuple[CheckState, ...], forge: str) -> str:
    # A gap closed: read the current world for the clear phrase or the finding line it recovered to.
    state = next((s for s in checks if s.check == check), None)
    if state is not None and state.status == "found" and state.cards:
        return "; ".join(card.text.rstrip(".") for card in state.cards)
    return check_hook_clear_copy(_as_check(check), forge)


def _shrank_default_note(check: str, forge: str) -> str:
    if check in {"conflict", "gate"}:
        return f"couldn't reach {_source_name(forge)}"
    return "the source can't be reached"


def appear_suppressed_keys(deltas: tuple[Delta, ...]) -> frozenset[str]:
    """Finding keys a fresh appearance already spoke: their steady bullet is suppressed."""

    return frozenset(delta.identity.key for delta in deltas if delta.direction == "appear")


def recovered_found_checks(deltas: tuple[Delta, ...]) -> frozenset[str]:
    """Checks whose recovery line carries the finding, so the steady found bullet is suppressed."""

    return frozenset(delta.check for delta in deltas if delta.direction == "transition")


def shrank_checks(deltas: tuple[Delta, ...]) -> frozenset[str]:
    """Checks a coverage-shrank line speaks, so the steady can't-verify line for them is dropped."""

    return frozenset(delta.check for delta in deltas if delta.direction == "coverage_shrank")


def bullet_suppressed(card: ContextCard, keys: frozenset[str], checks: frozenset[str]) -> bool:
    """A found card's steady bullet is suppressed when a fresh appearance already named it, or when
    the check recovered to it (its recovery line carries the finding). One fact, one voice."""

    key = card_finding_key(card)
    if key is not None and key in keys:
        return True
    check = REASON_PREFIX.get(card.reason_code.split(".", 1)[0])
    return check is not None and check in checks


def _as_check(check: str) -> CheckId:
    return cast("CheckId", check)


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
    forge = answer.request.forge
    headline = _HEADLINE[assessment.kind]
    if assessment.kind == "ready" and not any(s.status == "clear" for s in assessment.checks):
        # nothing ran at all (every check not configured): "clear" would be false comfort
        headline = "Nothing checked yet; here's why:"
    # The delta lane speaks first and once: what changed since work start, before the current world.
    lines = [*delta_lines(assessment.deltas, assessment.checks, forge), headline]
    lines.extend(_finding_bullets(assessment, forge))
    coverage = _coverage_line(answer, assessment)
    if coverage:
        lines.append(coverage)
    lines.extend(_fyi_lines(answer.selection))
    couldnt = _couldnt_check_line(assessment, forge)
    if couldnt:
        lines.append(couldnt)
    partially = _partially_checked_line(assessment)
    if partially:
        lines.append(partially)
    not_checked = _not_checked_line(assessment)
    if not_checked:
        lines.append(not_checked)
    still_running = _still_running_line(assessment)
    if still_running:
        lines.append(still_running)
    not_applicable = _not_applicable_line(assessment)
    if not_applicable:
        lines.append(not_applicable)
    lines.extend(_authority_block(answer.selection))
    return "\n".join(lines) + "\n"


def _finding_bullets(assessment: WorkStartAssessment, forge: str) -> list[str]:
    if assessment.kind == "heads_up":
        keys = appear_suppressed_keys(assessment.deltas)
        recovered = recovered_found_checks(assessment.deltas)
        bullets: list[str] = []
        for state in assessment.checks:
            if state.status == "found":
                bullets.extend(
                    f"  • {_finding_text(state, card)}"
                    for card in state.cards
                    if not bullet_suppressed(card, keys, recovered)
                )
        return bullets
    if assessment.kind == "cant_verify":
        return _cant_verify_bullets(assessment, forge)
    return []


def _finding_text(state: CheckState, card: ContextCard) -> str:
    action = RENDER_COPY[state.check].finding_action
    base = f"{card.text.rstrip('.')}: {action}" if action else card.text
    pr = _gh_hint(card) if state.check == "conflict" else ""
    return f"{base}{pr}"


def _gh_hint(card: ContextCard) -> str:
    provider = card.scope.get("provider")
    if provider is not None and provider != "github":
        return ""
    marker = card.source_display.rfind("#")
    if marker == -1:
        return ""
    digits = ""
    for ch in card.source_display[marker + 1:]:
        if ch.isdigit():
            digits += ch
        else:
            break
    if not digits:
        return ""
    repo = card.scope.get("repo")
    # carry --repo so the command works from any directory (and matches open-source)
    if isinstance(repo, str) and repo:
        return f" (gh pr view {digits} --repo {repo})"
    return f" (gh pr view {digits})"


def _cant_verify_bullets(assessment: WorkStartAssessment, forge: str) -> list[str]:
    # Every important non-clear check gets a bullet, so none is dropped: the combined
    # GitHub-unreachable bullet (to avoid repeating the long fix text when both are unreachable),
    # plus a bullet for each important pending check.
    status = {s.check: s.status for s in assessment.checks}
    stale_only = {
        s.check: bool(s.failing_sources) and all(st == "stale" for _, st in s.failing_sources)
        for s in assessment.checks
    }
    notes = {s.check: s.note for s in assessment.checks}
    # A coverage-shrank delta already speaks these checks ("... can no longer be verified"); drop
    # their steady can't-verify bullet so one fact gets one voice.
    shrank = shrank_checks(assessment.deltas)
    # A reached-but-not-confirmable source (a skipped pipeline, an unexhausted scan) must never
    # claim a connection problem: it gets its own note-led bullet instead of the fix text.
    conflict_unreachable = (
        status.get("conflict") == "unreachable"
        and not stale_only.get("conflict", False)
        and "conflict" not in shrank
    )
    gate_unreachable = (
        status.get("gate") == "unreachable"
        and not stale_only.get("gate", False)
        and "gate" not in shrank
    )
    fix = _fix_text(forge)
    bullets: list[str] = []
    for check in ("conflict", "gate"):
        if check in shrank:
            continue
        if status.get(check) == "unreachable" and stale_only.get(check) and notes.get(check):
            label = _conflict_label(forge) if check == "conflict" else _gate_label(forge)
            action = (
                "If a green build matters for this change, check the run yourself."
                if check == "gate"
                else f"Glance at {_source_name(forge)} yourself if this file is sensitive."
            )
            bullets.append(f"  • {label.capitalize()}: {notes[check]} {action}")
    if conflict_unreachable and gate_unreachable:
        bullets.append(
            f"  • {_conflict_label(forge)} and {_gate_label(forge)}: {fix} "
            f"Until it's back you won't see {_missing_both_phrase(forge)} on your files."
        )
    elif conflict_unreachable:
        bullets.append(
            f"  • {_conflict_label(forge)}: {fix} Until it's back you won't see "
            f"{_colliding_review_phrase(forge)} on your files."
        )
    elif gate_unreachable:
        bullets.append(
            f"  • {_gate_label(forge).capitalize()}: {fix} Until it's back you won't see "
            f"{_red_gate_phrase(forge)} on your files."
        )
    for state in assessment.checks:
        if state.status == "unbounded" and state.check in IMPORTANT_CHECKS:
            label = _conflict_label(forge) if state.check == "conflict" else _gate_label(forge)
            note = state.note or check_unreachable_copy(state.check, forge)
            bullets.append(
                f"  • {label}: {note} Glance at {_source_name(forge)} if this file is sensitive."
            )
    for state in assessment.checks:
        if state.status == "pending" and state.check in IMPORTANT_CHECKS:
            bullets.append(_pending_bullet(state.check))
    return bullets


def _coverage_line(answer: BrokerAnswer, assessment: WorkStartAssessment) -> str:
    clear = [_clear_phrase(answer, s) for s in assessment.checks if s.status == "clear"]
    if not clear:
        return ""
    label = "Checked: " if assessment.kind == "ready" else "Also checked: "
    return "  " + label + "; ".join(clear) + "."


def _clear_phrase(answer: BrokerAnswer, state: CheckState) -> str:
    phrase = check_clear_copy(state.check, answer.request.forge)
    if state.check == "criteria":
        suffix = _criteria_provenance_suffix(answer)
        if suffix:
            return f"{phrase} {suffix}"
    return phrase


def _criteria_provenance_suffix(answer: BrokerAnswer) -> str:
    issue_sources = [
        (issue, answer.request.input_provenance[f"issue:{issue}"])
        for issue in answer.request.linked_issues
        if f"issue:{issue}" in answer.request.input_provenance
    ]
    if not issue_sources:
        return ""
    described = [
        f"{issue} from {_issue_provenance_label(source)}" for issue, source in issue_sources
    ]
    if len(described) == 1:
        return f"(issue {described[0]})"
    return f"(issues {', '.join(described)})"


def _issue_provenance_label(source: str) -> str:
    if source == "a commit message trailer":
        return "a commit trailer"
    return source


def _fyi_lines(selection: ContextSelection) -> list[str]:
    return [
        f"  FYI: {entry.note}"
        for entry in selection.coverage.entries
        if entry.status == "fresh"
        and entry.visibility == "warning_when_relevant"
        and entry.note
    ]


def _couldnt_check_line(assessment: WorkStartAssessment, forge: str) -> str:
    # Surface every unreachable check that isn't already in the can't-verify bullets. Those
    # bullets only fire when kind == cant_verify and only for the important checks, so in any
    # other mode (a found check made it heads_up) the unreachable important checks must be
    # surfaced here too. Honest-UNKNOWN is never silently dropped.
    in_bullets = assessment.kind == "cant_verify"
    shrank = shrank_checks(assessment.deltas)
    gaps = [
        _unreachable_gap_copy(s, forge)
        for s in assessment.checks
        if s.status == "unreachable"
        and s.check not in shrank  # a coverage-shrank delta already speaks this check
        and not (in_bullets and s.check in IMPORTANT_CHECKS)
    ]
    if not gaps:
        return ""
    return "  Couldn't check: " + "; ".join(gaps) + "."


# The docs family can fail in two very different places AND in two very different ways; the
# parenthetical must name both truthfully: a Confluence budget hit or property-read failure was
# REACHED but not exhausted ("couldn't fully check"), while an unavailable space was not.
_DOCS_FAILURE_COPY = {
    ("docs_supersession", "unavailable"): "couldn't read the local docs folder",
    ("docs_supersession", "stale"): "couldn't fully check the local docs folder",
    ("confluence_pages", "unavailable"): "couldn't reach Confluence",
    ("confluence_pages", "stale"): "couldn't fully check Confluence",
}


def _unreachable_gap_copy(state: CheckState, forge: str) -> str:
    if state.check == "docs" and state.failing_sources:
        reasons = [
            _DOCS_FAILURE_COPY[pair] for pair in state.failing_sources if pair in _DOCS_FAILURE_COPY
        ]
        if reasons:
            return "the docs you rely on (" + "; ".join(reasons) + ")"
    if (
        state.failing_sources
        and all(st == "stale" for _, st in state.failing_sources)
        and state.note
    ):
        # reached but not confirmable: the connector's precise message, never "couldn't reach"
        label = _conflict_label(forge) if state.check == "conflict" else (
            _gate_label(forge) if state.check == "gate" else state.check
        )
        return f"{label} ({state.note.rstrip('.')})"
    return check_unreachable_copy(state.check, forge)


def _partially_checked_line(assessment: WorkStartAssessment) -> str:
    in_bullets = assessment.kind == "cant_verify"
    gaps = [
        s.note or RENDER_COPY[s.check].unreachable
        for s in assessment.checks
        if s.status == "unbounded"
        and not (in_bullets and s.check in IMPORTANT_CHECKS)
    ]
    if not gaps:
        return ""
    return "  Partially checked: " + "; ".join(gaps)


def _not_checked_line(assessment: WorkStartAssessment) -> str:
    gaps = [
        s.note or RENDER_COPY[s.check].not_checked
        for s in assessment.checks
        if s.status == "not_configured"
    ]
    if not gaps:
        return ""
    return "  Not checked: " + "; ".join(gaps) + "."


def _still_running_line(assessment: WorkStartAssessment) -> str:
    # An important pending check is already bulleted in cant_verify; surface the rest here so a
    # pending check is never dropped when a found elsewhere made the kind heads_up.
    in_bullets = assessment.kind == "cant_verify"
    gaps = [
        _pending_phrase(s.check)
        for s in assessment.checks
        if s.status == "pending" and not (in_bullets and s.check in IMPORTANT_CHECKS)
    ]
    if not gaps:
        return ""
    return "  Still running: " + "; ".join(gaps) + "."


def _not_applicable_line(assessment: WorkStartAssessment) -> str:
    gaps = [
        s.note or _not_applicable_phrase(s.check)
        for s in assessment.checks
        if s.status == "not_applicable"
    ]
    if not gaps:
        return ""
    return "  Not applicable: " + "; ".join(gaps) + "."


def _source_name(forge: str) -> str:
    return "GitLab" if forge == "gitlab" else "GitHub"


def _fix_text(forge: str) -> str:
    source = _source_name(forge)
    token = "GITLAB_TOKEN" if forge == "gitlab" else "GITHUB_TOKEN"
    return (
        f"teamctx couldn't reach {source}. Either it has no access yet (set {token}, or "
        f"{token}_FILE with a path to a token file) or it's a temporary connection issue."
    )


def _conflict_label(forge: str) -> str:
    return "Open MRs" if forge == "gitlab" else "Open PRs"


def _gate_label(forge: str) -> str:
    return "pipeline state" if forge == "gitlab" else "failing checks"


def _colliding_review_phrase(forge: str) -> str:
    return "colliding MRs" if forge == "gitlab" else "colliding PRs"


def _red_gate_phrase(forge: str) -> str:
    return "pipeline failures" if forge == "gitlab" else "red CI"


def _missing_both_phrase(forge: str) -> str:
    if forge == "gitlab":
        return "colliding MRs or pipeline failures"
    return "colliding PRs or red CI"


def _authority_block(selection: ContextSelection) -> list[str]:
    if not selection.authority:
        return []
    lines = ["", "Authority"]
    lines.extend(_authority_line(entry) for entry in selection.authority)
    return lines


def render_why(card: ContextCard) -> str:
    """Render the full evidence for one finding, plain prose.

    Covers: the finding text, why it matters, why teamctx flagged it, the source with
    freshness and confidence, and an honest note about body availability. Plain and
    decision-enabling; no jargon, no em dashes.
    """

    reason = card.reason.rstrip(".")
    lines = [
        card.text,
        f"  Why it matters: {card.why_this_matters}",
        f"  Why teamctx flagged it: {reason}.",
        f"  Source: {card.source_display} ({card.freshness}, {card.confidence} confidence).",
    ]
    if card.source_body == "status_only":
        lines.append("  teamctx shows metadata only here; it does not read the source body.")
    elif card.source_body == "blocked":
        lines.append("  Source body access is blocked by policy.")
    elif card.source_body == "unavailable":
        lines.append("  Source body is unavailable.")
    return "\n".join(lines) + "\n"


def render_open_source(card: ContextCard, open_targets: tuple[SourceOpenTarget, ...]) -> str:
    """Render how to open the source for one finding card.

    The opener command depends on the kind (pr, gate, criteria, doc). Body availability is
    stated honestly; when status-only, the note names it. If the card has a matched
    SourceOpenTarget its body_availability is used; otherwise card.source_body is the fallback.
    Plain, decision-enabling, no em dashes.
    """

    open_target = next(
        (t for t in open_targets if t.source_signal_id == card.refs[0]),
        None,
    )

    lines = [f"Open the source for {card.source_display}:"]

    if card.reason_code.startswith("collision"):
        pr_number = card.scope.get("pr_number")
        repo = card.scope.get("repo")
        url = card.scope.get("url")
        provider = card.scope.get("provider")
        is_github = provider is None or provider == "github"
        if is_github and pr_number is not None and isinstance(repo, str):
            lines.append(f"  gh pr view {pr_number} --repo {repo}")
        if isinstance(url, str) and is_github:
            lines.append(f"  or open {url}")
        elif isinstance(url, str):
            lines.append(f"  open {url}")
    elif card.reason_code.startswith("gate") or card.reason_code.startswith("criteria"):
        url = card.scope.get("url")
        if isinstance(url, str):
            lines.append(f"  open {url}")
    elif card.reason_code.startswith("doc"):
        url = card.scope.get("url")
        doc = card.scope.get("doc")
        if isinstance(url, str) and url:
            lines.append(f"  open {url}")
        elif isinstance(doc, str):
            lines.append(f"  open {doc}")

    availability = open_target.body_availability if open_target is not None else card.source_body
    if availability == "status_only":
        lines.append(
            "  teamctx shows metadata only; the source body is not included"
            " (status-only by policy)."
        )
    elif availability == "blocked":
        lines.append("  Source body access is blocked by policy.")
    elif availability == "unavailable":
        lines.append("  Source body is unavailable.")

    return "\n".join(lines) + "\n"
