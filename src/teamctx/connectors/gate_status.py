"""CI gate-status normalization.

Turns failing-gate facts into Core Contract V0 objects. No file/network I/O and no card
rendering — work-start DERIVES missed-gate cards from the signals emitted here.
"""

from __future__ import annotations

from collections.abc import Iterable
from dataclasses import dataclass
from typing import Literal

from teamctx.core.contracts import (
    CoreContractDocument,
    PolicyDecision,
    RequestContext,
    Scope,
    SourceSignal,
    SourceStatus,
    SourceStatusValue,
)


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
                id=f"sig_missed_gate_{_slug(gate.gate_name)}_{index}",
                signal_type="missed_gate",
                source_family="ci_deploy",
                scope=scope,
                evidence_summary=f"Required gate '{gate.gate_name}' is failing on this branch.",
                source_display=f"CI: {gate.gate_name}",
                freshness="fresh",
                confidence="high",
                visibility="visible",
                created_at=observed_at,
                observed_at=observed_at,
                expires_at=expires_at,
                policy=_policy_metadata_only(),
            )
        )
    source_statuses = [
        _ci_source_status(
            source_id=source_id,
            repo=request_context.repo,
            status="fresh",
            observed_at=observed_at,
            safe_user_message="CI check-run status refreshed.",
            visibility="silent",
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
    return CoreContractDocument(
        schema_version="teamctx.core_contract_document.v0",
        request_context=request_context,
        source_signals=[],
        source_statuses=[
            _ci_source_status(
                source_id=source_id,
                repo=repo,
                status=status,
                observed_at=observed_at,
                safe_user_message=safe_user_message,
                visibility="warning_when_relevant",
            )
        ],
        source_open_targets=[],
        guidance_records=[],
        session_context_uses=[],
        context_cards=[],
    )


def _ci_source_status(
    *,
    source_id: str,
    repo: str,
    status: SourceStatusValue,
    observed_at: str,
    safe_user_message: str,
    visibility: Literal["silent", "warning_when_relevant", "always"],
) -> SourceStatus:
    return SourceStatus(
        schema_version="teamctx.source_status.v0",
        source_id=source_id,
        source_family="ci_deploy",
        scope={"repo": repo},
        status=status,
        last_checked_at=observed_at if status != "stale" else None,
        safe_user_message=safe_user_message,
        normal_context_visibility=visibility,
        policy=_policy_metadata_only(),
    )


def _policy_metadata_only() -> PolicyDecision:
    return PolicyDecision(
        schema_version="teamctx.policy_decision.v0",
        can_render_to_user=True,
        can_render_to_agent=True,
        can_include_source_text=False,
        requires_review_for_guidance=False,
        decision_reason="CI gate status is allowed as evidence; source bodies are not included.",
    )


def _slug(name: str) -> str:
    return "".join(ch if ch.isalnum() else "_" for ch in name)
