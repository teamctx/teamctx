"""Versioned durable core contracts for TeamCtx.

These models are deliberately pure: validation is deterministic and has no file,
network, subprocess, randomness, or ambient-time dependency.
"""

from __future__ import annotations

from typing import Literal, Self

from pydantic import BaseModel, ConfigDict, Field, model_validator

SchemaVersion = Literal[
    "teamctx.policy_decision.v0",
    "teamctx.source_signal.v0",
    "teamctx.source_status.v0",
    "teamctx.source_open_target.v0",
    "teamctx.guidance_review.v0",
    "teamctx.guidance_record.v0",
    "teamctx.session_context_use.v0",
    "teamctx.context_card.v0",
    "teamctx.request_context.v0",
    "teamctx.core_contract_document.v0",
]
SignalType = Literal[
    "collision",
    "criteria_changed",
    "doc_superseded",
    "missed_gate",
    "changed_since_start",
    "stale_source",
    "unavailable_source",
    "blocked_source",
    "advisory_match",
    "explicit_handoff",
    "runtime_state",
]
SourceFamily = Literal[
    "local_workspace",
    "git_hosting",
    "issue_tracker",
    "docs",
    "local_notes",
    "ci_deploy",
    "chat_handoff",
    "project_guidance",
]
Freshness = Literal["fresh", "stale", "unavailable", "blocked", "disabled", "retired"]
Confidence = Literal["high", "medium", "low"]
Visibility = Literal["visible", "warning_only", "hidden", "never"]
SourceBodyState = Literal["openable", "status_only", "blocked", "unavailable", "not_collected"]
SourceStatusValue = Literal[
    "fresh", "stale", "unavailable", "blocked", "disabled", "pending", "not_applicable"
]
SourceStatusVisibility = Literal["silent", "warning_when_relevant", "always"]
GuidanceStatus = Literal["draft", "active", "retired"]
AgentInstruction = Literal["evidence_only", "verify_before_relying", "apply_when_in_scope"]
SectionName = Literal[
    "Needs attention",
    "Project guidance",
    "Verify before relying",
    "Source unavailable",
    "Good to know",
]
ScopeValue = str | int | float | bool | None | list[str]
Scope = dict[str, ScopeValue]


class ContractModel(BaseModel):
    """Base for V0 contracts: reject fields outside the published shape."""

    model_config = ConfigDict(extra="forbid")


class Severity(ContractModel):
    """Severity decomposition (kept for audit; the value is clamp01(kind_base ×
    (1 + alpha·magnitude_norm) × scope_mult)). Calibration of the constants is deferred."""

    value: float
    kind_base: float
    magnitude_norm: float
    scope_mult: float


class PolicyDecision(ContractModel):
    schema_version: Literal["teamctx.policy_decision.v0"]
    can_render_to_user: bool
    can_render_to_agent: bool
    can_include_source_text: bool
    requires_review_for_guidance: bool
    decision_reason: str

    @model_validator(mode="after")
    def _fail_closed_policy(self) -> Self:
        if not self.can_render_to_user and self.can_render_to_agent:
            raise ValueError("agent-visible policy requires user-visible policy")
        if self.can_include_source_text and not self.can_render_to_user:
            raise ValueError("source text requires user-visible policy")
        return self


class SourceSignal(ContractModel):
    schema_version: Literal["teamctx.source_signal.v0"]
    id: str
    signal_type: SignalType
    source_family: SourceFamily
    scope: Scope = Field(default_factory=dict)
    evidence_summary: str
    source_display: str
    freshness: Freshness
    confidence: Confidence
    visibility: Visibility
    created_at: str
    observed_at: str
    expires_at: str
    policy: PolicyDecision

    @model_validator(mode="after")
    def _fail_closed_visibility(self) -> Self:
        if self.visibility in {"hidden", "never"} and (
            self.policy.can_render_to_agent or self.policy.can_include_source_text
        ):
            raise ValueError("hidden source signals cannot render to agents or include text")
        if (
            self.freshness in {"blocked", "unavailable", "disabled"}
            and self.policy.can_include_source_text
        ):
            raise ValueError("blocked or unavailable source signals cannot include source text")
        return self


class SourceStatus(ContractModel):
    schema_version: Literal["teamctx.source_status.v0"]
    source_id: str
    source_family: SourceFamily
    scope: Scope = Field(default_factory=dict)
    status: SourceStatusValue
    last_checked_at: str | None
    safe_user_message: str
    normal_context_visibility: SourceStatusVisibility
    policy: PolicyDecision

    @model_validator(mode="after")
    def _fail_closed_status_visibility(self) -> Self:
        if self.status == "disabled" and self.normal_context_visibility == "always":
            raise ValueError("disabled sources cannot always render in normal context")
        if (
            self.status in {"blocked", "unavailable", "disabled"}
            and self.policy.can_include_source_text
        ):
            raise ValueError("unhealthy source status cannot include source text")
        return self


class SourceOpenTarget(ContractModel):
    schema_version: Literal["teamctx.source_open_target.v0"]
    id: str
    source_signal_id: str
    source_family: SourceFamily
    source_display: str
    open_label: str
    body_availability: Literal[
        "available", "status_only", "blocked", "unavailable", "not_collected"
    ]
    policy: PolicyDecision

    @model_validator(mode="after")
    def _fail_closed_source_opening(self) -> Self:
        if self.body_availability != "available" and self.policy.can_include_source_text:
            raise ValueError("only available source bodies may include source text")
        if self.body_availability == "available" and not self.policy.can_include_source_text:
            raise ValueError("available source bodies must be explicitly openable by policy")
        return self


class GuidanceReview(ContractModel):
    schema_version: Literal["teamctx.guidance_review.v0"]
    reviewed_by: str
    reviewed_at: str


class GuidanceRecord(ContractModel):
    schema_version: Literal["teamctx.guidance_record.v0"]
    id: str
    status: GuidanceStatus
    body: str
    scope: Scope = Field(default_factory=dict)
    source_display: str
    review: GuidanceReview | None
    freshness: Freshness
    confidence: Confidence
    policy: PolicyDecision

    @model_validator(mode="after")
    def _active_guidance_requires_review(self) -> Self:
        if self.status == "active" and self.review is None:
            raise ValueError("active guidance requires review metadata")
        if self.status != "active" and self.policy.can_render_to_agent:
            raise ValueError("draft or retired guidance cannot render to the agent")
        if self.status == "retired" and self.freshness != "retired":
            raise ValueError("retired guidance must use retired freshness")
        return self


class SessionContextUse(ContractModel):
    schema_version: Literal["teamctx.session_context_use.v0"]
    id: str
    session_id: str
    card_ids: list[str] = Field(default_factory=list)
    signal_ids: list[str] = Field(default_factory=list)
    guidance_ids: list[str] = Field(default_factory=list)
    created_at: str
    expires_at: str
    agent_visible: bool

    @model_validator(mode="after")
    def _requires_selection(self) -> Self:
        if not self.card_ids and not self.signal_ids and not self.guidance_ids:
            raise ValueError("session context use requires at least one selected object")
        return self


class ContextCard(ContractModel):
    schema_version: Literal["teamctx.context_card.v0"]
    id: str
    section: SectionName
    text: str
    why_this_matters: str
    source_display: str
    refs: list[str] = Field(min_length=1)
    reason: str
    scope: Scope = Field(default_factory=dict)
    freshness: Freshness
    confidence: Confidence
    source_body: SourceBodyState
    source_open_target_id: str | None = None
    agent_instruction: AgentInstruction
    reason_code: str = ""
    severity: Severity | None = None

    @model_validator(mode="after")
    def _openable_cards_have_target(self) -> Self:
        if self.source_body == "openable" and self.source_open_target_id is None:
            raise ValueError("openable cards require a source open target")
        if self.section == "Project guidance" and self.agent_instruction != "apply_when_in_scope":
            raise ValueError("project guidance cards must apply only when in scope")
        return self


class RequestContext(ContractModel):
    schema_version: Literal["teamctx.request_context.v0"]
    request_id: str
    repo: str
    branch: str | None = None
    task: str
    paths: list[str] = Field(default_factory=list)
    linked_issues: list[str] = Field(default_factory=list)
    input_provenance: dict[str, str] = Field(default_factory=dict)
    requested_at: str
    requesting_principal: str | None = None


class CoreContractDocument(ContractModel):
    schema_version: Literal["teamctx.core_contract_document.v0"]
    request_context: RequestContext
    source_signals: list[SourceSignal] = Field(default_factory=list)
    source_statuses: list[SourceStatus] = Field(default_factory=list)
    source_open_targets: list[SourceOpenTarget] = Field(default_factory=list)
    guidance_records: list[GuidanceRecord] = Field(default_factory=list)
    session_context_uses: list[SessionContextUse] = Field(default_factory=list)
    context_cards: list[ContextCard] = Field(default_factory=list)

    @model_validator(mode="after")
    def _validate_references(self) -> Self:
        signal_ids = {signal.id for signal in self.source_signals}
        guidance_ids = {guidance.id for guidance in self.guidance_records}
        card_ids = {card.id for card in self.context_cards}
        open_target_ids = {target.id for target in self.source_open_targets}
        known_card_refs = signal_ids | guidance_ids | {
            status.source_id for status in self.source_statuses
        }

        for target in self.source_open_targets:
            if target.source_signal_id not in signal_ids:
                raise ValueError(f"source open target {target.id} references unknown signal")

        for card in self.context_cards:
            missing_refs = [ref for ref in card.refs if ref not in known_card_refs]
            if missing_refs:
                raise ValueError(f"context card {card.id} references unknown ids")
            if (
                card.source_open_target_id is not None
                and card.source_open_target_id not in open_target_ids
            ):
                raise ValueError(f"context card {card.id} references unknown source open target")
            if card.section == "Project guidance" and not any(
                ref in guidance_ids for ref in card.refs
            ):
                raise ValueError("project guidance cards must reference a guidance record")

        for use in self.session_context_uses:
            if any(card_id not in card_ids for card_id in use.card_ids):
                raise ValueError(f"session context use {use.id} references unknown card")
            if any(signal_id not in signal_ids for signal_id in use.signal_ids):
                raise ValueError(f"session context use {use.id} references unknown signal")
            if any(guidance_id not in guidance_ids for guidance_id in use.guidance_ids):
                raise ValueError(f"session context use {use.id} references unknown guidance")

        return self


def load_core_contract_document(data: object) -> CoreContractDocument:
    """Validate a parsed V0 contract fixture."""

    return CoreContractDocument.model_validate(data)
