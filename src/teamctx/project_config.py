"""Project-local TeamCtx configuration."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Literal

from pydantic import BaseModel, ConfigDict, ValidationError


class ProjectConfigError(ValueError):
    """Raised when project config cannot be loaded or validated."""


class StrictConfigModel(BaseModel):
    model_config = ConfigDict(extra="forbid")


class GitHubSourceConfig(StrictConfigModel):
    repo: str
    token_env: str = "GITHUB_TOKEN"
    include_title: bool = False


class ProjectConfig(StrictConfigModel):
    schema_version: Literal["teamctx.project_config.v0"]
    github: GitHubSourceConfig | None = None
    default_output: str = ".teamctx/context.json"


def load_project_config(path: Path) -> ProjectConfig:
    try:
        raw = path.read_text(encoding="utf-8")
    except OSError as exc:
        raise ProjectConfigError(f"Could not read project config: {path}") from exc

    try:
        data = json.loads(raw)
    except json.JSONDecodeError as exc:
        raise ProjectConfigError(f"Project config is not valid JSON: {path}") from exc

    try:
        return ProjectConfig.model_validate(data)
    except ValidationError as exc:
        message = f"Project config does not match teamctx.project_config.v0: {path}"
        raise ProjectConfigError(message) from exc


def maybe_load_project_config(path: Path) -> ProjectConfig | None:
    if not path.exists():
        return None
    return load_project_config(path)
