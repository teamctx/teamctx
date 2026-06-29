"""Pure finding-query module: resolve a typed selector to one current finding card.

A selector is a short handle the user types in `why` or `open-source` commands to address
a specific finding. The module is pure: it only reads the cards already in a BrokerAnswer
and raises typed exceptions when the selector does not match exactly one card. No I/O.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Literal

from teamctx.core.contracts import ContextCard

FindingSelectorKind = Literal["pr", "issue", "path", "doc", "gate"]

_ALLOWED_KINDS: frozenset[str] = frozenset({"pr", "issue", "path", "doc", "gate"})
_ALLOWED_FORMS = "pr:N, issue:REF, path:X, doc:PATH, gate:NAME"


@dataclass(frozen=True)
class FindingSelector:
    kind: FindingSelectorKind
    value: str


class FindingSelectorError(ValueError):
    """The selector text is malformed or uses an unknown kind."""


class NoFindingMatch(LookupError):  # noqa: N818
    """Zero finding cards match the selector."""


class AmbiguousFinding(LookupError):  # noqa: N818
    """More than one finding card matches the selector."""


def parse_selector(text: str) -> FindingSelector:
    """Parse a selector string like ``pr:7`` or ``gate:unit-tests`` into a FindingSelector.

    Raises FindingSelectorError if the text is malformed or the kind is not recognised.
    """

    if ":" not in text:
        raise FindingSelectorError(
            f"Invalid selector {text!r}: expected one of {_ALLOWED_FORMS}."
        )
    kind, _, value = text.partition(":")
    if kind not in _ALLOWED_KINDS:
        raise FindingSelectorError(
            f"Unknown selector kind {kind!r}: allowed forms are {_ALLOWED_FORMS}."
        )
    if kind == "pr" and not value.isdigit():
        raise FindingSelectorError(
            f"pr: selector expects a number, for example pr:7 (got {value!r})."
        )
    return FindingSelector(kind=kind, value=value)  # type: ignore[arg-type]


def _normalize_issue(v: str) -> str:
    """Ensure the issue ref has a leading ``#`` so ``42`` and ``#42`` both match ``#42``."""

    return v if v.startswith("#") else f"#{v}"


def _specific_selector(card: ContextCard) -> str:
    """Return the most-specific alternative selector for this card."""

    if card.reason_code.startswith("collision"):
        pr_num = card.scope.get("pr_number")
        if pr_num is not None:
            return f"pr:{pr_num}"
    elif card.reason_code.startswith("criteria"):
        issue = card.scope.get("issue")
        if isinstance(issue, str):
            return f"issue:{issue}"
    elif card.reason_code.startswith("gate"):
        gate = card.scope.get("gate")
        if isinstance(gate, str):
            return f"gate:{gate}"
    elif card.reason_code.startswith("doc"):
        doc = card.scope.get("doc")
        if isinstance(doc, str):
            return f"doc:{doc}"
    return card.id


def match_finding(cards: tuple[ContextCard, ...], selector: FindingSelector) -> ContextCard:
    """Return the ONE finding card that matches the selector.

    Raises NoFindingMatch if zero cards match, AmbiguousFinding if more than one match.
    The path: selector is the only one that legitimately matches multiple cards (any card
    whose scope files list contains the path), so it is the usual source of AmbiguousFinding.
    """

    matched: list[ContextCard] = []

    if selector.kind == "pr":
        try:
            pr_num = int(selector.value)
        except ValueError as exc:
            raise FindingSelectorError(
                f"pr: selector expects a number, got {selector.value!r}."
            ) from exc
        for card in cards:
            if (
                card.reason_code.startswith("collision")
                and card.scope.get("pr_number") == pr_num
            ):
                matched.append(card)

    elif selector.kind == "issue":
        normalized = _normalize_issue(selector.value)
        for card in cards:
            if card.reason_code.startswith("criteria"):
                scope_issue = card.scope.get("issue")
                if isinstance(scope_issue, str) and _normalize_issue(scope_issue) == normalized:
                    matched.append(card)

    elif selector.kind == "gate":
        for card in cards:
            if (
                card.reason_code.startswith("gate")
                and card.scope.get("gate") == selector.value
            ):
                matched.append(card)

    elif selector.kind == "doc":
        for card in cards:
            if (
                card.reason_code.startswith("doc")
                and card.scope.get("doc") == selector.value
            ):
                matched.append(card)

    elif selector.kind == "path":
        for card in cards:
            files = card.scope.get("files")
            if isinstance(files, list) and selector.value in files:
                matched.append(card)

    selector_text = f"{selector.kind}:{selector.value}"

    if len(matched) == 0:
        raise NoFindingMatch(
            f"No current finding matches `{selector_text}`. It may have cleared since you "
            f"last ran work-start, or there was nothing to find."
        )

    if len(matched) > 1:
        options = ", ".join(f"`{_specific_selector(card)}`" for card in matched)
        raise AmbiguousFinding(
            f"`{selector_text}` matches {len(matched)} findings: {options}. "
            f"Use a more specific selector to narrow it down."
        )

    return matched[0]
