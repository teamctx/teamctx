"""Expected-vs-actual matching for the Phase 5 emulation harness.

An expected block is a template with byte-exact literal spans and templated placeholders.
Matching escapes the literal spans (byte-exact, per the program spec's "stable copy" rule) and
matches placeholders by pattern (templated): ``{n}`` a run of digits, ``{url}`` a URL token,
``{id}`` an opaque id token. A row PASSES when every required block matches somewhere in the
actual output and no forbidden literal appears; otherwise it FAILS. Deterministic, stdlib only.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from typing import Literal

Status = Literal["PASS", "FAIL", "SKIP"]

# Placeholder -> the regex that matches that templated span. Greedy over non-whitespace is correct
# for our blocks: placeholders are whitespace- or punctuation-delimited in the renderer copy.
_PLACEHOLDER_PATTERN: dict[str, str] = {
    "{n}": r"\d+",
    "{url}": r"\S+",
    "{id}": r"\S+",
}
_TOKEN_RE = re.compile(r"\{n\}|\{url\}|\{id\}")


def compile_template(template: str) -> re.Pattern[str]:
    """Compile one expected block into a regex: literal spans escaped (byte-exact), placeholders
    replaced by their templated pattern. Raises ValueError on an unknown ``{...}`` token so a typo
    in an expected block is never silently treated as a literal that can't match."""

    _reject_unknown_tokens(template)
    parts: list[str] = []
    index = 0
    for match in _TOKEN_RE.finditer(template):
        parts.append(re.escape(template[index : match.start()]))
        parts.append(_PLACEHOLDER_PATTERN[match.group(0)])
        index = match.end()
    parts.append(re.escape(template[index:]))
    return re.compile("".join(parts), re.DOTALL)


def _reject_unknown_tokens(template: str) -> None:
    for candidate in re.findall(r"\{[a-z]+\}", template):
        if candidate not in _PLACEHOLDER_PATTERN:
            raise ValueError(
                f"unknown expected-block placeholder {candidate!r}; "
                f"known placeholders are {sorted(_PLACEHOLDER_PATTERN)}"
            )


@dataclass(frozen=True)
class BlockOutcome:
    """One expected-block check against the actual output."""

    subject: str
    kind: Literal["present", "absent"]
    ok: bool


@dataclass(frozen=True)
class Expectation:
    """What a row asserts about one actual output.

    ``must_match`` are expected blocks (templates); each must match somewhere in the actual.
    ``must_absent`` are literal strings that must NOT appear (e.g. a false all-clear line the
    row is proving never shows). A row can carry several expectations, one per transport.
    """

    must_match: tuple[str, ...] = ()
    must_absent: tuple[str, ...] = ()


def evaluate(actual: str, expectation: Expectation) -> tuple[Status, tuple[BlockOutcome, ...]]:
    """Match ``actual`` against ``expectation``; return (PASS/FAIL, per-block outcomes)."""

    outcomes: list[BlockOutcome] = []
    for template in expectation.must_match:
        found = compile_template(template).search(actual) is not None
        outcomes.append(BlockOutcome(subject=template, kind="present", ok=found))
    for literal in expectation.must_absent:
        outcomes.append(BlockOutcome(subject=literal, kind="absent", ok=literal not in actual))
    status: Status = "PASS" if all(outcome.ok for outcome in outcomes) else "FAIL"
    return status, tuple(outcomes)


@dataclass(frozen=True)
class RowResult:
    """The verdict for one scenario row, plus the actual output captured as evidence."""

    row_id: str
    title: str
    status: Status
    outcomes: tuple[BlockOutcome, ...] = ()
    actual: str = ""
    note: str = ""


def passed_or_failed(
    row_id: str, title: str, actual: str, expectation: Expectation, *, note: str = ""
) -> RowResult:
    """Run one expectation over one actual output and package the RowResult."""

    status, outcomes = evaluate(actual, expectation)
    return RowResult(
        row_id=row_id, title=title, status=status, outcomes=outcomes, actual=actual, note=note
    )


def combine(row_id: str, title: str, parts: list[RowResult], *, actual: str = "") -> RowResult:
    """Fold several sub-evaluations (one per transport) into one RowResult. FAIL if any part
    fails; the actual evidence is the concatenation unless an explicit ``actual`` is given."""

    outcomes: tuple[BlockOutcome, ...] = ()
    chunks: list[str] = []
    for part in parts:
        outcomes = outcomes + part.outcomes
        if part.actual:
            chunks.append(f"--- {part.note or part.title} ---\n{part.actual}")
    status: Status = "PASS" if all(outcome.ok for outcome in outcomes) else "FAIL"
    return RowResult(
        row_id=row_id,
        title=title,
        status=status,
        outcomes=outcomes,
        actual=actual or "\n\n".join(chunks),
    )


def skipped(row_id: str, title: str, note: str) -> RowResult:
    """A row that is not yet wired: reported honestly, never PASS and never FAIL."""

    return RowResult(row_id=row_id, title=title, status="SKIP", note=note)


@dataclass(frozen=True)
class ProgramResult:
    """The whole matrix run."""

    rows: tuple[RowResult, ...] = field(default_factory=tuple)

    @property
    def failed(self) -> tuple[RowResult, ...]:
        return tuple(row for row in self.rows if row.status == "FAIL")

    @property
    def ok(self) -> bool:
        return not self.failed
