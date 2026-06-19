"""Authority: governance declarations, separate from observed evidence.

Authority answers *what should be true* (declared), never *what is observed*. The broker
**surfaces conflict and refuses to adjudicate**, and **never lets a fresh lower-priority
source override a stale higher-priority one** — silently falling through to the fresh lower
source would be exactly the absence-implies-safety failure the model forbids.

Declarations are assumed already projected to the consumer-visible set (Delta_P): the loader
filters by ``can_read`` before passing them here, so authority over invisible sources
contributes nothing (preserving existence-privacy).

Pure: dataclasses + typing only (the core purity test guards it).
"""

from __future__ import annotations

from collections.abc import Iterable
from dataclasses import dataclass
from typing import Literal

AuthorityState = Literal[
    "resolved",
    "missing",
    "conflicted",
    "unknown[stale-authority]",
]


@dataclass(frozen=True)
class AuthorityDecl:
    """A governance declaration: a ``source`` is authoritative for ``subject`` at ``priority``,
    declaring ``value``; ``fresh`` is whether the declaring source is within its window."""

    subject: str
    source: str
    priority: int
    value: str
    fresh: bool


@dataclass(frozen=True)
class AuthorityEntry:
    """The resolved authority state for a subject. ``value`` is set only when ``resolved``."""

    subject: str
    state: AuthorityState
    value: str | None


def assess_authority(subject: str, declarations: Iterable[AuthorityDecl]) -> AuthorityEntry:
    """Resolve the authority state for ``subject`` over the (already P-visible) declarations.

    ``missing`` if none apply; ``unknown[stale-authority]`` if the priority-maximal authority
    is present but stale (never overridden by a fresh lower-priority source); ``conflicted``
    if two or more fresh priority-maximal declarations disagree (refuse to pick); ``resolved``
    only when a unique fresh priority-maximal value stands.
    """

    applies = [decl for decl in declarations if decl.subject == subject]
    if not applies:
        return AuthorityEntry(subject, "missing", None)

    max_priority = max(decl.priority for decl in applies)
    maximal = [decl for decl in applies if decl.priority == max_priority]
    fresh_maximal = [decl for decl in maximal if decl.fresh]
    if not fresh_maximal:
        return AuthorityEntry(subject, "unknown[stale-authority]", None)

    values = {decl.value for decl in fresh_maximal}
    if len(values) > 1:
        return AuthorityEntry(subject, "conflicted", None)
    return AuthorityEntry(subject, "resolved", next(iter(values)))
