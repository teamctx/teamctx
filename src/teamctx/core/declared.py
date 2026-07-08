"""Pure evaluation for config-declared checks."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Literal

from teamctx.core.contracts import (
    ClosureEntry,
    ContextCard,
    RequestContext,
    SourceDocument,
    SourceSignal,
    SourceStatus,
)
from teamctx.core.evaluate import Valuation

DeclaredMatchOp = Literal["equality", "presence", "prefix", "threshold"]
DeclaredComparator = Literal[">", ">=", "<", "<=", "=="]
DeclaredProfile = Literal["reflex", "full"]
DeclaredLane = Literal["important", "fyi"]
DeclaredCheckStatus = Literal["clear", "found", "unreachable"]
JsonScalar = str | int | float | bool | None

DECLARED_SOURCE_SCOPE_KEY = "teamctx_declared_source_id"
DECLARED_CHECK_SCOPE_KEY = "teamctx_check_id"
DECLARED_IDENTITY_SCOPE_KEY = "teamctx_identity_key"


@dataclass(frozen=True)
class DeclaredCheckCopy:
    clear: str
    finding: str
    couldnt_check: str
    not_enabled: str


@dataclass(frozen=True)
class DeclaredMatchRule:
    op: DeclaredMatchOp
    field: str | None = None
    value: JsonScalar = None
    comparator: DeclaredComparator | None = None
    left: str | None = None
    right: str | None = None


@dataclass(frozen=True)
class DeclaredCheckDefinition:
    id: str
    claim: str
    consumes: str
    match: DeclaredMatchRule
    copy: DeclaredCheckCopy
    identity: tuple[str, ...]
    lane: DeclaredLane
    profile: DeclaredProfile


@dataclass(frozen=True)
class DeclaredCheckEvaluation:
    check_id: str
    status: DeclaredCheckStatus
    valuation: Valuation
    closure: ClosureEntry
    cards: tuple[ContextCard, ...] = ()
    note: str | None = None
    failing_sources: tuple[tuple[str, str], ...] = ()


@dataclass(frozen=True)
class _MatchResult:
    value: bool | None
    reason: str = ""


def evaluate_declared_checks(
    request: RequestContext,
    checks: tuple[DeclaredCheckDefinition, ...],
    signals: tuple[SourceSignal, ...],
    statuses: tuple[SourceStatus, ...],
    source_documents: tuple[SourceDocument, ...],
) -> tuple[DeclaredCheckEvaluation, ...]:
    return tuple(
        evaluate_declared_check(
            request,
            check,
            signals=signals,
            statuses=statuses,
            source_documents=source_documents,
        )
        for check in checks
    )


def evaluate_declared_check(
    request: RequestContext,
    check: DeclaredCheckDefinition,
    *,
    signals: tuple[SourceSignal, ...],
    statuses: tuple[SourceStatus, ...],
    source_documents: tuple[SourceDocument, ...],
) -> DeclaredCheckEvaluation:
    consumed_ids = _consumed_document_ids(check.consumes, source_documents)
    source_statuses = tuple(status for status in statuses if status.source_id == check.consumes)
    unhealthy = tuple(status for status in source_statuses if status.status != "fresh")
    if unhealthy:
        note = "; ".join(
            status.safe_user_message for status in unhealthy if status.safe_user_message
        )
        return _unknown(check, consumed_ids=consumed_ids, note=note or None, statuses=unhealthy)
    if not source_statuses:
        return _unknown(check, consumed_ids=consumed_ids, note="declared source was not fetched")

    signal = _record_signal(check.consumes, signals)
    if signal is None:
        return _unknown(
            check,
            consumed_ids=consumed_ids,
            note="declared source did not provide a mapped record",
        )

    record = _record_from_signal(signal)
    result = _match_record(
        check.match,
        record,
        request=request,
        document_observed_at=signal.observed_at,
    )
    if result.value is None:
        return _unknown(check, consumed_ids=consumed_ids, note=result.reason)
    if not result.value:
        return DeclaredCheckEvaluation(
            check_id=check.id,
            status="clear",
            valuation=Valuation("true"),
            closure=ClosureEntry(
                check_id=check.id,
                proposition=check.claim,
                consumed_document_ids=consumed_ids,
                closure_status="complete",
                reason=f"declared check {check.id} evaluated configured match",
            ),
        )

    card = _declared_card(check, signal, record)
    return DeclaredCheckEvaluation(
        check_id=check.id,
        status="found",
        valuation=Valuation("false"),
        closure=ClosureEntry(
            check_id=check.id,
            proposition=check.claim,
            consumed_document_ids=consumed_ids,
            closure_status="complete",
            reason=f"declared check {check.id} evaluated configured match",
        ),
        cards=(card,),
    )


def disabled_declared_closure(check: DeclaredCheckDefinition) -> ClosureEntry:
    return ClosureEntry(
        check_id=check.id,
        proposition=check.claim,
        consumed_document_ids=(),
        closure_status="disabled-by-team",
        reason=f"check {check.id} is not enabled by the team",
    )


def _unknown(
    check: DeclaredCheckDefinition,
    *,
    consumed_ids: tuple[str, ...],
    note: str | None,
    statuses: tuple[SourceStatus, ...] = (),
) -> DeclaredCheckEvaluation:
    return DeclaredCheckEvaluation(
        check_id=check.id,
        status="unreachable",
        valuation=Valuation("unknown", "incomplete[stale-dep]"),
        closure=ClosureEntry(
            check_id=check.id,
            proposition=check.claim,
            consumed_document_ids=consumed_ids,
            closure_status="incomplete[stale-dep]",
            reason=note or f"declared check {check.id} could not fully evaluate",
        ),
        note=note,
        failing_sources=tuple((status.source_id, status.status) for status in statuses),
    )


def _record_signal(source_id: str, signals: tuple[SourceSignal, ...]) -> SourceSignal | None:
    for signal in signals:
        if (
            signal.signal_type == "advisory_match"
            and signal.scope.get(DECLARED_SOURCE_SCOPE_KEY) == source_id
        ):
            return signal
    return None


def _record_from_signal(signal: SourceSignal) -> dict[str, JsonScalar]:
    record: dict[str, JsonScalar] = {}
    for key, value in signal.scope.items():
        if key.startswith("teamctx_"):
            continue
        if isinstance(value, (str, int, float, bool)) or value is None:
            record[key] = value
    return record


def _declared_card(
    check: DeclaredCheckDefinition,
    signal: SourceSignal,
    record: dict[str, JsonScalar],
) -> ContextCard:
    scope = dict(signal.scope)
    scope[DECLARED_CHECK_SCOPE_KEY] = check.id
    scope[DECLARED_IDENTITY_SCOPE_KEY] = _identity_key(check, record)
    return ContextCard(
        schema_version="teamctx.context_card.v0",
        id=f"card_{check.id}_{signal.id}",
        section="Verify before relying",
        text=check.copy.finding,
        why_this_matters=check.claim,
        source_display=signal.source_display,
        refs=[signal.id],
        reason=check.claim,
        scope=scope,
        freshness=signal.freshness,
        confidence=signal.confidence,
        source_body="status_only",
        source_open_target_id=None,
        agent_instruction="verify_before_relying",
        reason_code=f"declared.{check.id}",
        severity=None,
    )


def _identity_key(check: DeclaredCheckDefinition, record: dict[str, JsonScalar]) -> str:
    parts = [f"{field}={record.get(field)!r}" for field in check.identity]
    return "|".join(parts)


def _consumed_document_ids(
    source_id: str, source_documents: tuple[SourceDocument, ...]
) -> tuple[str, ...]:
    return tuple(
        sorted(
            document.document_id
            for document in source_documents
            if source_id in document.source_ids
        )
    )


def _match_record(
    rule: DeclaredMatchRule,
    record: dict[str, JsonScalar],
    *,
    request: RequestContext,
    document_observed_at: str,
) -> _MatchResult:
    if rule.op == "presence":
        if rule.field is None:
            return _MatchResult(None, "presence match is missing its field")
        if rule.field not in record:
            return _MatchResult(None, f"field {rule.field} is missing")
        value = record[rule.field]
        return _MatchResult(value is not None and value != "")

    if rule.op == "equality":
        if rule.field is None:
            return _MatchResult(None, "equality match is missing its field")
        if rule.field not in record:
            return _MatchResult(None, f"field {rule.field} is missing")
        return _MatchResult(record[rule.field] == rule.value)

    if rule.op == "prefix":
        if rule.field is None:
            return _MatchResult(None, "prefix match is missing its field")
        if rule.field not in record:
            return _MatchResult(None, f"field {rule.field} is missing")
        field_value = record[rule.field]
        if not isinstance(field_value, str) or not isinstance(rule.value, str):
            return _MatchResult(False)
        return _MatchResult(field_value.startswith(rule.value))

    return _threshold_match(
        rule,
        record,
        request=request,
        document_observed_at=document_observed_at,
    )


def _threshold_match(
    rule: DeclaredMatchRule,
    record: dict[str, JsonScalar],
    *,
    request: RequestContext,
    document_observed_at: str,
) -> _MatchResult:
    comparator = rule.comparator
    if comparator is None:
        return _MatchResult(None, "threshold match is missing its comparator")
    left_token = rule.left or rule.field
    if left_token is None:
        return _MatchResult(None, "threshold match is missing its left operand")
    right_token = rule.right
    left = _resolve_operand(
        left_token,
        record,
        request=request,
        document_observed_at=document_observed_at,
    )
    right = (
        _resolve_operand(
            right_token,
            record,
            request=request,
            document_observed_at=document_observed_at,
        )
        if right_token is not None
        else _ResolvedOperand(value=rule.value, is_time=False)
    )
    if left.missing:
        return _MatchResult(None, f"field {left_token} is missing")
    if right.missing:
        return _MatchResult(None, f"field {right_token} is missing")
    if left.is_time or right.is_time:
        left_time = _utc_tuple(left.value)
        right_time = _utc_tuple(right.value)
        if left_time is None:
            return _MatchResult(None, f"time operand {left_token} is malformed")
        if right_time is None:
            name = right_token if right_token is not None else "value"
            return _MatchResult(None, f"time operand {name} is malformed")
        return _MatchResult(_compare_time(left_time, right_time, comparator))
    left_number = _number(left.value)
    right_number = _number(right.value)
    if left_number is None or right_number is None:
        return _MatchResult(None, "threshold operands must be numbers or UTC times")
    return _MatchResult(_compare_number(left_number, right_number, comparator))


@dataclass(frozen=True)
class _ResolvedOperand:
    value: JsonScalar
    is_time: bool
    missing: bool = False


def _resolve_operand(
    token: str | None,
    record: dict[str, JsonScalar],
    *,
    request: RequestContext,
    document_observed_at: str,
) -> _ResolvedOperand:
    if token is None:
        return _ResolvedOperand(None, is_time=False, missing=True)
    if token == "request.requested_at":
        return _ResolvedOperand(request.requested_at, is_time=True)
    if token == "document.observed_at":
        return _ResolvedOperand(document_observed_at, is_time=True)
    if token not in record:
        return _ResolvedOperand(None, is_time=False, missing=True)
    return _ResolvedOperand(record[token], is_time=False)


def _number(value: JsonScalar) -> float | None:
    if isinstance(value, bool) or value is None:
        return None
    if isinstance(value, (int, float)):
        return float(value)
    if isinstance(value, str):
        try:
            return float(value)
        except ValueError:
            return None
    return None


def _compare_time(left: tuple[int, ...], right: tuple[int, ...], op: str) -> bool:
    if op == ">":
        return left > right
    if op == ">=":
        return left >= right
    if op == "<":
        return left < right
    if op == "<=":
        return left <= right
    return left == right


def _compare_number(left: float, right: float, op: str) -> bool:
    if op == ">":
        return left > right
    if op == ">=":
        return left >= right
    if op == "<":
        return left < right
    if op == "<=":
        return left <= right
    return left == right


def _utc_tuple(value: JsonScalar) -> tuple[int, ...] | None:
    if not isinstance(value, str):
        return None
    text = value
    if text.endswith("Z"):
        text = text[:-1]
    elif text.endswith("+00:00"):
        text = text[:-6]
    else:
        return None
    if "T" not in text:
        return None
    date_part, time_part = text.split("T", 1)
    date_bits = date_part.split("-")
    time_bits = time_part.split(":")
    if len(date_bits) != 3 or len(time_bits) != 3:
        return None
    second_part = time_bits[2]
    if "." in second_part:
        seconds, fraction = second_part.split(".", 1)
        if not fraction.isdigit():
            return None
        fraction_value = int((fraction + "000000")[:6])
    else:
        seconds = second_part
        fraction_value = 0
    pieces = [*date_bits, time_bits[0], time_bits[1], seconds]
    if not all(piece.isdigit() for piece in pieces):
        return None
    year, month, day, hour, minute, second = (int(piece) for piece in pieces)
    if not (1 <= month <= 12 and 1 <= day <= 31 and hour <= 23 and minute <= 59 and second <= 60):
        return None
    return (year, month, day, hour, minute, second, fraction_value)
