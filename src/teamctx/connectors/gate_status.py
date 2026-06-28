"""CI gate-status normalization.

Turns failing-gate facts into Core Contract V0 objects. No file/network I/O and no card
rendering; work-start DERIVES missed-gate cards from the signals emitted here.
"""

from __future__ import annotations

from collections.abc import Iterable
from dataclasses import dataclass

from teamctx.connectors._contract import (
    metadata_only_policy,
    slug,
    source_status,
    unavailable_document,
)
from teamctx.core.contracts import (
    CoreContractDocument,
    RequestContext,
    Scope,
    SourceFamily,
    SourceSignal,
    SourceStatusValue,
)

_POLICY_REASON = "CI gate status is allowed as evidence; source bodies are not included."
_SOURCE_FAMILY: SourceFamily = "ci_deploy"


@dataclass(frozen=True)
class FailingGate:
    """A required CI gate that is failing. ``files`` are repo-relative POSIX paths the gate
    covers (v1: the request paths, since the gate is whole-repo)."""

    repo: str
    gate_name: str
    url: str
    files: tuple[str, ...]


def normalize_failing_gates(
    request_context: RequestContext,
    gates: Iterable[FailingGate],
    *,
    observed_at: str,
    expires_at: str = "next_refresh",
    source_id: str = "github_check_runs",
    coverage_truncated: bool = False,
) -> CoreContractDocument:
    source_signals: list[SourceSignal] = []
    for index, gate in enumerate(gates):
        scope: Scope = {
            "repo": gate.repo,
            "files": list(gate.files),
            "gate": gate.gate_name,
            "url": gate.url,
        }
        source_signals.append(
            SourceSignal(
                schema_version="teamctx.source_signal.v0",
                id=f"sig_missed_gate_{slug(gate.gate_name)}_{index}",
                signal_type="missed_gate",
                source_family=_SOURCE_FAMILY,
                scope=scope,
                evidence_summary=f"Required gate '{gate.gate_name}' is failing on this branch.",
                source_display=f"CI: {gate.gate_name}",
                freshness="fresh",
                confidence="high",
                visibility="visible",
                created_at=observed_at,
                observed_at=observed_at,
                expires_at=expires_at,
                policy=metadata_only_policy(_POLICY_REASON),
            )
        )
    _status: SourceStatusValue = "stale" if coverage_truncated else "fresh"
    _safe_msg = (
        "Checked the first 100 check runs for this ref; there are more, "
        "so this is not a complete check."
        if coverage_truncated
        else "CI check-run status refreshed."
    )
    source_statuses = [
        source_status(
            source_id=source_id,
            source_family=_SOURCE_FAMILY,
            scope={"repo": request_context.repo},
            status=_status,
            observed_at=observed_at,
            safe_user_message=_safe_msg,
            visibility="silent",
            policy_reason=_POLICY_REASON,
        )
    ]
    return CoreContractDocument(
        schema_version="teamctx.core_contract_document.v0",
        request_context=request_context,
        source_signals=source_signals,
        source_statuses=source_statuses,
        source_open_targets=[],
        guidance_records=[],
        session_context_uses=[],
        context_cards=[],
    )


def unavailable_gates_document(
    request_context: RequestContext,
    *,
    repo: str,
    observed_at: str,
    source_id: str = "github_check_runs",
    status: SourceStatusValue = "unavailable",
    safe_user_message: str,
) -> CoreContractDocument:
    return unavailable_document(
        request_context,
        source_id=source_id,
        source_family=_SOURCE_FAMILY,
        scope={"repo": repo},
        observed_at=observed_at,
        status=status,
        safe_user_message=safe_user_message,
        policy_reason=_POLICY_REASON,
    )
