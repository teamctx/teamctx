"""Project-local TeamCtx configuration."""

from __future__ import annotations

import json
import re
from pathlib import Path
from typing import Literal, cast

from pydantic import BaseModel, ConfigDict, Field, ValidationError, field_validator, model_validator

from teamctx import __version__
from teamctx.config_failure import TEAM_CONFIG_UPGRADE_LINE
from teamctx.connectors.declared_file import DeclaredFileSource
from teamctx.core.declared import (
    DeclaredCheckCopy,
    DeclaredCheckDefinition,
    DeclaredMatchRule,
)
from teamctx.core.kinds import (
    CARD_KINDS,
    DEFAULT_CHECK_IDS,
    DEFAULT_IMPORTANT_CHECKS,
    CheckId,
    CheckLane,
    CheckSelection,
    resolve_check_selection,
)
from teamctx.git_context import ForgeProvider
from teamctx.strict_json import StrictJsonError, loads_strict_json

DEFAULT_CONFIG_PATH = Path(".teamctx/config.json")
TEAMCTX_VERSION = __version__
_DECLARED_ID = re.compile(r"^x_[a-z0-9_]+$")
_FIELD_ID = re.compile(r"^[a-zA-Z0-9_]+$")
_MAX_COPY_CHARS = 240
_BUILT_IN_CHECK_IDS = frozenset(DEFAULT_CHECK_IDS)
_RESERVED_DISPLAY_PHRASES = frozenset(
    phrase.casefold()
    for phrase in (
        "open PRs",
        "spec changes",
        "docs",
        "failing checks",
        *(kind.check_id for kind in CARD_KINDS),
        *(kind.claim.proposition for kind in CARD_KINDS),
        *(kind.copy.coverage.clear for kind in CARD_KINDS),
        *(kind.copy.coverage.not_checked for kind in CARD_KINDS),
        *(kind.copy.coverage.unreachable for kind in CARD_KINDS),
        *(kind.copy.finding.action for kind in CARD_KINDS),
    )
    if phrase
)


class ProjectConfigError(ValueError):
    """Raised when project config cannot be loaded or validated."""


class StrictConfigModel(BaseModel):
    model_config = ConfigDict(extra="forbid", populate_by_name=True)


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


JsonScalar = str | int | float | bool | None


class DeclaredSourceConfig(StrictConfigModel):
    kind: Literal["file", "url"]
    path: str | None = None
    schema_map: dict[str, str]

    @model_validator(mode="after")
    def validate_declared_source(self) -> DeclaredSourceConfig:
        if self.kind == "url":
            raise ValueError("URL declared sources are not supported in this version")
        if not self.path:
            raise ValueError("file declared sources must set path")
        _validate_relative_declared_path(self.path)
        if not self.schema_map:
            raise ValueError("declared sources must map at least one field")
        for field, pointer in self.schema_map.items():
            if not _FIELD_ID.fullmatch(field):
                raise ValueError(f"declared source field {field!r} must use letters, digits, or _")
            if not isinstance(pointer, str) or (pointer != "" and not pointer.startswith("/")):
                raise ValueError(f"schema_map pointer for {field} must be a JSON pointer")
        return self


class DeclaredMatchConfig(StrictConfigModel):
    op: Literal["equality", "presence", "prefix", "threshold"]
    field: str | None = None
    value: JsonScalar = None
    comparator: Literal[">", ">=", "<", "<=", "=="] | None = None
    left: str | None = None
    right: str | None = None

    @model_validator(mode="after")
    def validate_match_shape(self) -> DeclaredMatchConfig:
        if self.op in {"equality", "presence", "prefix"} and not self.field:
            raise ValueError(f"{self.op} match must set field")
        if self.op == "prefix" and not isinstance(self.value, str):
            raise ValueError("prefix match must set a string value")
        if self.op == "threshold" and self.comparator is None:
            raise ValueError("threshold match must set comparator")
        if self.op != "threshold" and (self.left is not None or self.right is not None):
            raise ValueError(f"{self.op} match cannot set left or right operands")
        return self


class DeclaredCheckCopyConfig(StrictConfigModel):
    clear: str
    finding: str
    couldnt_check: str
    not_enabled: str

    @field_validator("clear", "finding", "couldnt_check", "not_enabled")
    @classmethod
    def sanitize_copy(cls, value: str) -> str:
        return _sanitize_config_string(value)


class CheckConfig(StrictConfigModel):
    enabled: bool
    lane: str | None = None
    consumes: str | None = None
    profile: Literal["reflex", "full"] | None = None
    claim: str | None = None
    match: DeclaredMatchConfig | None = None
    declared_copy: DeclaredCheckCopyConfig | None = Field(default=None, alias="copy")
    identity: tuple[str, ...] | None = None


class ProjectConfig(StrictConfigModel):
    schema_version: Literal["teamctx.project_config.v0"]
    requires_teamctx: str | None = None
    work_start: WorkStartConfig | None = None
    checks: dict[CheckId, CheckConfig] | None = None
    declared_sources: dict[str, DeclaredSourceConfig] | None = None

    @model_validator(mode="after")
    def require_supported_teamctx(self) -> ProjectConfig:
        if self.requires_teamctx is not None and _version_lt(
            TEAMCTX_VERSION, self.requires_teamctx
        ):
            raise ValueError(TEAM_CONFIG_UPGRADE_LINE)
        _validate_project_declarations(self)
        return self


def build_work_start_project_config(
    *, repo: str, forge: ForgeProvider = "github", docs_root: str | None = None
) -> ProjectConfig:
    return ProjectConfig(
        schema_version="teamctx.project_config.v0",
        work_start=WorkStartConfig(repo=repo, forge=forge, docs_root=docs_root),
    )


def check_selection_for_project_config(config: ProjectConfig | None) -> CheckSelection:
    if config is None or config.checks is None:
        return resolve_check_selection()
    checks = config.checks
    enabled: list[CheckId] = []
    important: list[CheckId] = []
    disabled: list[CheckId] = []
    for check_id in DEFAULT_CHECK_IDS:
        check_config = checks.get(check_id)
        if check_config is not None and check_config.enabled:
            enabled.append(check_id)
            lane = check_config.lane or (
                "important" if check_id in DEFAULT_IMPORTANT_CHECKS else "fyi"
            )
            if lane == "important":
                important.append(check_id)
        else:
            disabled.append(check_id)
    for check_id, check_config in checks.items():
        if check_id in _BUILT_IN_CHECK_IDS:
            continue
        if check_config.enabled:
            enabled.append(check_id)
            if check_config.lane == "important":
                important.append(check_id)
        else:
            disabled.append(check_id)
    return CheckSelection(
        enabled_checks=tuple(enabled),
        important_checks=tuple(important),
        disabled_checks=tuple(disabled),
    )


def declared_file_sources_for_project_config(
    config: ProjectConfig | None,
) -> tuple[DeclaredFileSource, ...]:
    if config is None or not config.declared_sources:
        return ()
    return tuple(
        DeclaredFileSource(
            id=source_id,
            path=cast(str, source.path),
            schema_map=tuple(source.schema_map.items()),
        )
        for source_id, source in config.declared_sources.items()
    )


def declared_checks_for_project_config(
    config: ProjectConfig | None,
    *,
    enabled: bool | None = None,
) -> tuple[DeclaredCheckDefinition, ...]:
    if config is None or not config.checks:
        return ()
    definitions: list[DeclaredCheckDefinition] = []
    for check_id, check in config.checks.items():
        if check_id in _BUILT_IN_CHECK_IDS:
            continue
        if enabled is not None and check.enabled != enabled:
            continue
        definitions.append(_declared_check_definition(check_id, check))
    return tuple(definitions)


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
        data = loads_strict_json(raw, source=source)
    except StrictJsonError as exc:
        raise ProjectConfigError(str(exc)) from exc

    try:
        return ProjectConfig.model_validate(data)
    except ValidationError as exc:
        if _is_upgrade_validation_error(data, exc):
            raise ProjectConfigError(TEAM_CONFIG_UPGRADE_LINE) from exc
        message = (
            f"Project config does not match teamctx.project_config.v0: {source}: "
            f"{_first_validation_message(exc)}"
        )
        raise ProjectConfigError(message) from exc


def _looks_like_future_team_config(data: object) -> bool:
    if not isinstance(data, dict):
        return False
    future_team_semantics = {"checks", "requires_teamctx", "declared_sources", "sources"}
    return any(key in data for key in future_team_semantics)


def _is_upgrade_validation_error(data: object, exc: ValidationError) -> bool:
    for error in exc.errors():
        message = str(error.get("msg", ""))
        if TEAM_CONFIG_UPGRADE_LINE in message:
            return True
        if error.get("type") == "extra_forbidden" and _looks_like_future_team_config(data):
            return True
    return False


def _first_validation_message(exc: ValidationError) -> str:
    errors = exc.errors()
    if not errors:
        return "invalid project config"
    message = str(errors[0].get("msg", "invalid project config"))
    prefix = "Value error, "
    if message.startswith(prefix):
        return message[len(prefix):]
    return message


def _declared_check_definition(check_id: str, check: CheckConfig) -> DeclaredCheckDefinition:
    if (
        check.consumes is None
        or check.claim is None
        or check.match is None
        or check.declared_copy is None
        or check.identity is None
        or check.lane is None
        or check.profile is None
    ):
        raise ValueError(f"declared check {check_id} is incomplete")
    return DeclaredCheckDefinition(
        id=check_id,
        claim=check.claim,
        consumes=check.consumes,
        match=DeclaredMatchRule(
            op=check.match.op,
            field=check.match.field,
            value=check.match.value,
            comparator=check.match.comparator,
            left=check.match.left,
            right=check.match.right,
        ),
        copy=DeclaredCheckCopy(
            clear=check.declared_copy.clear,
            finding=check.declared_copy.finding,
            couldnt_check=check.declared_copy.couldnt_check,
            not_enabled=check.declared_copy.not_enabled,
        ),
        identity=check.identity,
        lane=cast(CheckLane, check.lane),
        profile=check.profile,
    )


def _validate_project_declarations(config: ProjectConfig) -> None:
    source_ids = tuple((config.declared_sources or {}).keys())
    check_ids = tuple((config.checks or {}).keys())
    _validate_declared_id_set(source_ids, label="declared source")
    _validate_check_ids_and_shapes(config)
    declared_check_ids = tuple(key for key in check_ids if key.startswith("x_"))
    _validate_casefold_collisions((*source_ids, *declared_check_ids))


def _validate_declared_id_set(ids: tuple[str, ...], *, label: str) -> None:
    for item_id in ids:
        _validate_declared_id(item_id, label=label)


def _validate_declared_id(item_id: str, *, label: str) -> None:
    folded = item_id.casefold()
    if item_id != folded or not _DECLARED_ID.fullmatch(folded):
        raise ValueError(f"{label} id {item_id!r} must match x_[a-z0-9_]+")
    if folded in _BUILT_IN_CHECK_IDS:
        raise ValueError(f"{label} id {item_id!r} is reserved")


def _validate_casefold_collisions(ids: tuple[str, ...]) -> None:
    seen: dict[str, str] = {}
    for item_id in ids:
        folded = item_id.casefold()
        previous = seen.get(folded)
        if previous is not None:
            raise ValueError(f"declared id {item_id!r} collides with {previous!r}")
        seen[folded] = item_id


def _validate_check_ids_and_shapes(config: ProjectConfig) -> None:
    if not config.checks:
        return
    source_ids = set((config.declared_sources or {}).keys())
    for check_id, check in config.checks.items():
        if check.lane is not None and check.lane not in {"important", "fyi"}:
            raise ValueError(TEAM_CONFIG_UPGRADE_LINE)
        if check_id in _BUILT_IN_CHECK_IDS:
            _validate_builtin_check_shape(check_id, check)
            continue
        _validate_declared_id(check_id, label="declared check")
        if _bare_future_check(check):
            raise ValueError(TEAM_CONFIG_UPGRADE_LINE)
        _validate_declared_check_shape(check_id, check, source_ids=source_ids, config=config)


def _validate_builtin_check_shape(check_id: str, check: CheckConfig) -> None:
    if any(
        value is not None
        for value in (
            check.consumes,
            check.profile,
            check.claim,
            check.match,
            check.declared_copy,
            check.identity,
        )
    ):
        raise ValueError(TEAM_CONFIG_UPGRADE_LINE)


def _bare_future_check(check: CheckConfig) -> bool:
    return (
        check.consumes is None
        and check.profile is None
        and check.claim is None
        and check.match is None
        and check.declared_copy is None
        and check.identity is None
    )


def _validate_declared_check_shape(
    check_id: str,
    check: CheckConfig,
    *,
    source_ids: set[str],
    config: ProjectConfig,
) -> None:
    missing = [
        name
        for name, value in (
            ("consumes", check.consumes),
            ("claim", check.claim),
            ("match", check.match),
            ("copy", check.declared_copy),
            ("identity", check.identity),
            ("lane", check.lane),
            ("profile", check.profile),
        )
        if value is None
    ]
    if missing:
        raise ValueError(f"declared check {check_id} must set {', '.join(missing)}")
    assert check.consumes is not None
    assert check.identity is not None
    assert check.match is not None
    assert check.declared_copy is not None
    if check.consumes not in source_ids:
        raise ValueError(f"declared check {check_id} consumes unknown source {check.consumes}")
    mapped_fields = set(config.declared_sources[check.consumes].schema_map)  # type: ignore[index]
    if not check.identity:
        raise ValueError(f"declared check {check_id} identity must name at least one field")
    for field in check.identity:
        if field not in mapped_fields:
            raise ValueError(f"declared check {check_id} identity field {field} is not mapped")
    for field in _match_fields(check.match):
        if field not in mapped_fields:
            raise ValueError(f"declared check {check_id} match field {field} is not mapped")
    _validate_no_shadowing(check_id, check)


def _match_fields(match: DeclaredMatchConfig) -> tuple[str, ...]:
    fields: list[str] = []
    for value in (match.field, match.left, match.right):
        if value is None or value in {"request.requested_at", "document.observed_at"}:
            continue
        fields.append(value)
    return tuple(fields)


def _validate_no_shadowing(check_id: str, check: CheckConfig) -> None:
    assert check.claim is not None
    assert check.declared_copy is not None
    values = (
        check_id,
        check.claim,
        check.declared_copy.clear,
        check.declared_copy.finding,
        check.declared_copy.couldnt_check,
        check.declared_copy.not_enabled,
    )
    for value in values:
        if value.casefold() in _RESERVED_DISPLAY_PHRASES:
            raise ValueError(f"declared check {check_id} uses reserved built-in copy")


def _validate_relative_declared_path(path: str) -> None:
    pure = Path(path)
    if pure.is_absolute():
        raise ValueError(f"declared file source path must be relative: {path}")
    parts = path.replace("\\", "/").split("/")
    if ".git" in parts:
        raise ValueError(f"declared file source path must not be under .git: {path}")
    if any(part == ".." for part in parts):
        raise ValueError(f"declared file source path must stay inside the project root: {path}")


def _sanitize_config_string(value: str) -> str:
    stripped = "".join(ch for ch in value if ord(ch) >= 32 and ord(ch) != 127)
    return stripped[:_MAX_COPY_CHARS]


def _version_lt(current: str, required: str) -> bool:
    return _version_tuple(current) < _version_tuple(required)


def _version_tuple(value: str) -> tuple[int, ...]:
    parts = value.split(".")
    if not parts:
        raise ValueError(f"invalid version: {value!r}")
    parsed: list[int] = []
    for part in parts:
        if not part.isdigit():
            raise ValueError(f"invalid version: {value!r}")
        parsed.append(int(part))
    return tuple(parsed)


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
