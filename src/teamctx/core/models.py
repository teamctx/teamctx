"""Pydantic models for the fixture-backed prototype."""

from __future__ import annotations

from typing import Any

from pydantic import BaseModel, ConfigDict, Field


class StrictModel(BaseModel):
    """Base model that rejects fields the prototype does not understand."""

    model_config = ConfigDict(extra="forbid")


class SignalPolicy(StrictModel):
    can_render_to_user: bool
    can_render_to_agent: bool
    can_include_source_text: bool
    requires_review_for_guidance: bool


class SourceSignal(StrictModel):
    id: str
    signal_type: str
    source_family: str
    scope: dict[str, Any] = Field(default_factory=dict)
    evidence_summary: str
    source_display: str
    freshness: str
    confidence: str
    visibility: str
    created_at: str
    observed_at: str
    expires_at: str
    policy: SignalPolicy


class GuidanceRecord(StrictModel):
    id: str
    status: str
    body: str
    scope: dict[str, Any] = Field(default_factory=dict)
    source_display: str
    freshness: str
    confidence: str


class ContextCard(StrictModel):
    id: str
    section: str
    text: str
    why_this_matters: str
    source: str
    refs: list[str]
    default_agent_visible: bool = True
    relevance: str | None = None
    why_hidden_by_default: str | None = None


class Fixture(StrictModel):
    fixture_id: str
    date: str
    task: str
    scope: dict[str, Any] = Field(default_factory=dict)
    source_signals: list[SourceSignal]
    guidance_records: list[GuidanceRecord]
    expected_cards: list[ContextCard]


class SessionSelection(StrictModel):
    session_id: str
    card_ids: list[str] = Field(default_factory=list)
