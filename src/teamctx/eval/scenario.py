"""Eval scenarios, expressed in the contracts model.

A scenario is the input to one A/B trial: a task, the request context, and the source
signals/statuses the REAL engine derives cards from. Optional workspace files describe the
disposable repo the agent works in. There is no hand-authored ``expected_cards``; the cards
come from ``broker_answer``, so the eval tests the live engine.
"""

from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path

from pydantic import BaseModel, ConfigDict, Field, ValidationError

from teamctx.core.contracts import RequestContext, SourceSignal, SourceStatus


class EvalScenarioError(ValueError):
    """Raised when a scenario file cannot be loaded or validated."""


class WorkspaceFile(BaseModel):
    model_config = ConfigDict(extra="forbid")
    path: str
    content: str


class _ScenarioFile(BaseModel):
    """Strict on-disk shape. Signals/statuses validate as the real contracts model."""

    model_config = ConfigDict(extra="forbid")
    scenario_id: str
    task: str
    request: RequestContext
    signals: list[SourceSignal] = Field(default_factory=list)
    statuses: list[SourceStatus] = Field(default_factory=list)
    workspace_files: list[WorkspaceFile] = Field(default_factory=list)


@dataclass(frozen=True)
class EvalScenario:
    scenario_id: str
    task: str
    request: RequestContext
    signals: tuple[SourceSignal, ...]
    statuses: tuple[SourceStatus, ...]
    workspace_files: tuple[WorkspaceFile, ...] = ()


def scenario_from_document(document: _ScenarioFile) -> EvalScenario:
    return EvalScenario(
        scenario_id=document.scenario_id,
        task=document.task,
        request=document.request,
        signals=tuple(document.signals),
        statuses=tuple(document.statuses),
        workspace_files=tuple(document.workspace_files),
    )


def load_scenario(path: Path) -> EvalScenario:
    try:
        raw = path.read_text(encoding="utf-8")
    except OSError as exc:
        raise EvalScenarioError(f"Could not read scenario: {path}") from exc
    try:
        data = json.loads(raw)
    except json.JSONDecodeError as exc:
        raise EvalScenarioError(f"Scenario is not valid JSON: {path}") from exc
    try:
        document = _ScenarioFile.model_validate(data)
    except ValidationError as exc:
        raise EvalScenarioError(f"Scenario does not match the contracts model: {path}") from exc
    return scenario_from_document(document)


def scenario_paths(scenarios_dir: Path) -> list[Path]:
    return sorted(path for path in scenarios_dir.glob("*.json") if path.is_file())
