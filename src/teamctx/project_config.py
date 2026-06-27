"""Project-local TeamCtx configuration."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Literal

from pydantic import BaseModel, ConfigDict, ValidationError

DEFAULT_CONFIG_PATH = Path(".teamctx/config.json")
DEFAULT_OUTPUT_PATH = ".teamctx/context.json"


class ProjectConfigError(ValueError):
    """Raised when project config cannot be loaded or validated."""


class StrictConfigModel(BaseModel):
    model_config = ConfigDict(extra="forbid")


class GitHubSourceConfig(StrictConfigModel):
    repo: str
    token_env: str = "GITHUB_TOKEN"
    include_title: bool = False


class WorkStartConfig(StrictConfigModel):
    """Project-stable inputs for the work-start broker, shared across actors (committed).
    Per-actor secrets (the token) live in the environment, never here."""

    repo: str | None = None
    docs_root: str | None = None


class ProjectConfig(StrictConfigModel):
    schema_version: Literal["teamctx.project_config.v0"]
    github: GitHubSourceConfig | None = None
    default_output: str = DEFAULT_OUTPUT_PATH
    work_start: WorkStartConfig | None = None


def build_project_config(
    *,
    github_repo: str,
    token_env: str = "GITHUB_TOKEN",
    include_title: bool = False,
    default_output: str = DEFAULT_OUTPUT_PATH,
) -> ProjectConfig:
    return ProjectConfig(
        schema_version="teamctx.project_config.v0",
        github=GitHubSourceConfig(
            repo=github_repo,
            token_env=token_env,
            include_title=include_title,
        ),
        default_output=default_output,
    )


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


def write_project_config(path: Path, config: ProjectConfig, *, overwrite: bool = False) -> None:
    if path.exists() and not overwrite:
        raise ProjectConfigError(f"Project config already exists: {path}")

    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps(config.model_dump(mode="json"), indent=2) + "\n",
        encoding="utf-8",
    )
