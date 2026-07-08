"""Project-local TeamCtx configuration."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Literal

from pydantic import BaseModel, ConfigDict, ValidationError, field_validator

from teamctx.config_failure import TEAM_CONFIG_UPGRADE_LINE
from teamctx.git_context import ForgeProvider

DEFAULT_CONFIG_PATH = Path(".teamctx/config.json")


class ProjectConfigError(ValueError):
    """Raised when project config cannot be loaded or validated."""


class StrictConfigModel(BaseModel):
    model_config = ConfigDict(extra="forbid")


class JiraConfig(StrictConfigModel):
    base_url: str

    @field_validator("base_url")
    @classmethod
    def normalize_base_url(cls, value: str) -> str:
        return value.rstrip("/")


class ConfluenceConfig(StrictConfigModel):
    base_url: str
    space_key: str

    @field_validator("base_url")
    @classmethod
    def normalize_base_url(cls, value: str) -> str:
        stripped = value.rstrip("/")
        if stripped.endswith("/wiki"):
            stripped = stripped.removesuffix("/wiki")
        return stripped.rstrip("/")


class WorkStartConfig(StrictConfigModel):
    """Project-stable inputs for the work-start broker, shared across actors (committed).
    Per-actor secrets (the token) live in the environment, never here."""

    repo: str | None = None
    forge: ForgeProvider = "github"
    docs_root: str | None = None
    jira: JiraConfig | None = None
    confluence: ConfluenceConfig | None = None


class ProjectConfig(StrictConfigModel):
    schema_version: Literal["teamctx.project_config.v0"]
    work_start: WorkStartConfig | None = None


def build_work_start_project_config(
    *, repo: str, forge: ForgeProvider = "github", docs_root: str | None = None
) -> ProjectConfig:
    return ProjectConfig(
        schema_version="teamctx.project_config.v0",
        work_start=WorkStartConfig(repo=repo, forge=forge, docs_root=docs_root),
    )


def load_project_config(path: Path) -> ProjectConfig:
    try:
        raw = path.read_text(encoding="utf-8")
    except OSError as exc:
        raise ProjectConfigError(f"Could not read project config: {path}") from exc

    return parse_project_config_text(raw, str(path))


def parse_project_config_bytes(raw: bytes, source: str) -> ProjectConfig:
    try:
        text = raw.decode("utf-8")
    except UnicodeDecodeError as exc:
        raise ProjectConfigError(f"Project config is not valid UTF-8: {source}") from exc
    return parse_project_config_text(text, source)


def parse_project_config_text(raw: str, source: str) -> ProjectConfig:
    try:
        data = json.loads(raw)
    except json.JSONDecodeError as exc:
        raise ProjectConfigError(f"Project config is not valid JSON: {source}") from exc

    try:
        return ProjectConfig.model_validate(data)
    except ValidationError as exc:
        if _looks_like_future_team_config(data):
            raise ProjectConfigError(TEAM_CONFIG_UPGRADE_LINE) from exc
        message = f"Project config does not match teamctx.project_config.v0: {source}"
        raise ProjectConfigError(message) from exc


def _looks_like_future_team_config(data: object) -> bool:
    if not isinstance(data, dict):
        return False
    future_team_semantics = {"checks", "requires_teamctx", "declared_sources", "sources"}
    return any(key in data for key in future_team_semantics)


def maybe_load_project_config(path: Path) -> ProjectConfig | None:
    if not path.exists():
        return None
    return load_project_config(path)


def write_project_config(
    path: Path,
    config: ProjectConfig,
    *,
    overwrite: bool = False,
    exclude_defaults: bool = False,
) -> None:
    if path.exists() and not overwrite:
        raise ProjectConfigError(f"Project config already exists: {path}")

    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps(config.model_dump(mode="json", exclude_defaults=exclude_defaults), indent=2)
        + "\n",
        encoding="utf-8",
    )
