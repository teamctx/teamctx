"""Generic connector for config-declared in-repo JSON record files."""

from __future__ import annotations

import subprocess
from dataclasses import dataclass
from pathlib import Path, PurePosixPath
from typing import Any

from teamctx.connectors._contract import metadata_only_policy, slug, source_status
from teamctx.core.contracts import CoreContractDocument, RequestContext, Scope, SourceSignal
from teamctx.core.declared import DECLARED_SOURCE_SCOPE_KEY, JsonScalar
from teamctx.strict_json import StrictJsonError, loads_strict_json

MAX_DECLARED_FILE_BYTES = 64 * 1024
MAX_DECLARED_RECORD_DEPTH = 12
MAX_DECLARED_FIELD_CHARS = 240


@dataclass(frozen=True)
class DeclaredFileSource:
    id: str
    path: str
    schema_map: tuple[tuple[str, str], ...]


def run_declared_file_sources(
    sources: tuple[DeclaredFileSource, ...],
    *,
    request_context: RequestContext,
    observed_at: str,
    project_root: Path,
) -> list[CoreContractDocument]:
    return [
        run_declared_file_source(
            source,
            request_context=request_context,
            observed_at=observed_at,
            project_root=project_root,
        )
        for source in sources
    ]


def run_declared_file_source(
    source: DeclaredFileSource,
    *,
    request_context: RequestContext,
    observed_at: str,
    project_root: Path,
) -> CoreContractDocument:
    reason = _validate_worktree_path(project_root, source.path)
    if reason is not None:
        return _unavailable(source, request_context, observed_at, reason)

    blob = _read_head_blob(project_root, source.path)
    if blob is None:
        if (project_root / source.path).exists():
            reason = f"commit {source.path} to activate declared file source {source.id}"
        else:
            reason = f"declared file source {source.id} is missing from HEAD at {source.path}"
        return _unavailable(source, request_context, observed_at, reason)
    if blob.kind != "regular":
        return _unavailable(
            source,
            request_context,
            observed_at,
            f"declared file source {source.id} is not a regular file in HEAD",
        )
    if len(blob.data) > MAX_DECLARED_FILE_BYTES:
        return _unavailable(
            source,
            request_context,
            observed_at,
            (
                f"declared file source {source.id} is too large; maximum is "
                f"{MAX_DECLARED_FILE_BYTES} bytes"
            ),
        )

    try:
        record = loads_strict_json(
            blob.data,
            source=source.path,
            max_bytes=MAX_DECLARED_FILE_BYTES,
            max_depth=MAX_DECLARED_RECORD_DEPTH,
        )
        mapped = _pluck_record(source, record)
    except (StrictJsonError, ValueError) as exc:
        return _unavailable(source, request_context, observed_at, str(exc))

    return _fresh(source, request_context, observed_at, mapped)


@dataclass(frozen=True)
class _HeadBlob:
    data: bytes
    kind: str


def _read_head_blob(root: Path, rel_path: str) -> _HeadBlob | None:
    mode = _head_mode(root, rel_path)
    if mode is None:
        return None
    kind = "regular" if mode.startswith("100") else "other"
    try:
        result = subprocess.run(
            ["git", "-C", str(root), "show", f"HEAD:{rel_path}"],
            capture_output=True,
            check=True,
            timeout=10,
        )
    except (OSError, subprocess.CalledProcessError, subprocess.TimeoutExpired):
        return None
    return _HeadBlob(data=result.stdout, kind=kind)


def _head_mode(root: Path, rel_path: str) -> str | None:
    try:
        result = subprocess.run(
            ["git", "-C", str(root), "ls-tree", "HEAD", "--", rel_path],
            capture_output=True,
            check=True,
            text=True,
            timeout=10,
        )
    except (OSError, subprocess.CalledProcessError, subprocess.TimeoutExpired):
        return None
    line = result.stdout.strip()
    if not line:
        return None
    return line.split(maxsplit=1)[0]


def _validate_worktree_path(root: Path, rel_path: str) -> str | None:
    pure = PurePosixPath(rel_path)
    if pure.is_absolute():
        return f"declared file source path must be relative: {rel_path}"
    if ".git" in pure.parts:
        return f"declared file source path must not be under .git: {rel_path}"
    base = root.resolve()
    target = (root / rel_path)
    try:
        resolved = target.resolve()
        resolved.relative_to(base)
    except (OSError, ValueError):
        return f"declared file source path escapes the project root: {rel_path}"
    if target.exists():
        if target.is_symlink():
            return f"declared file source path must be a regular file, not a symlink: {rel_path}"
        if not target.is_file():
            return f"declared file source path must be a regular file: {rel_path}"
    return None


def _pluck_record(source: DeclaredFileSource, record: Any) -> dict[str, JsonScalar]:
    mapped: dict[str, JsonScalar] = {}
    for field, pointer in source.schema_map:
        value, present = _json_pointer(record, pointer)
        if not present:
            continue
        if not (isinstance(value, (str, int, float, bool)) or value is None):
            raise ValueError(
                f"declared file source {source.id} mapped field {field} is not a scalar"
            )
        mapped[field] = _sanitize_value(value)
    return mapped


def _json_pointer(record: Any, pointer: str) -> tuple[Any, bool]:
    if pointer == "":
        return record, True
    if not pointer.startswith("/"):
        raise ValueError(f"schema_map pointer must start with /: {pointer}")
    current = record
    for raw_part in pointer.split("/")[1:]:
        part = raw_part.replace("~1", "/").replace("~0", "~")
        if isinstance(current, dict):
            if part not in current:
                return None, False
            current = current[part]
        elif isinstance(current, list):
            if not part.isdigit():
                return None, False
            index = int(part)
            if index >= len(current):
                return None, False
            current = current[index]
        else:
            return None, False
    return current, True


def _sanitize_value(value: JsonScalar) -> JsonScalar:
    if not isinstance(value, str):
        return value
    stripped = "".join(ch for ch in value if ord(ch) >= 32 and ord(ch) != 127)
    return stripped[:MAX_DECLARED_FIELD_CHARS]


def _fresh(
    source: DeclaredFileSource,
    request_context: RequestContext,
    observed_at: str,
    mapped: dict[str, JsonScalar],
) -> CoreContractDocument:
    scope: Scope = {DECLARED_SOURCE_SCOPE_KEY: source.id, **mapped}
    signal = SourceSignal(
        schema_version="teamctx.source_signal.v0",
        id=f"sig_declared_{slug(source.id)}",
        signal_type="advisory_match",
        source_family="project_guidance",
        scope=scope,
        evidence_summary=f"Declared file source {source.id} was read.",
        source_display=source.path,
        freshness="fresh",
        confidence="high",
        visibility="visible",
        created_at=observed_at,
        observed_at=observed_at,
        expires_at="next_refresh",
        policy=metadata_only_policy("declared record fields are mapped metadata only"),
    )
    return CoreContractDocument(
        schema_version="teamctx.core_contract_document.v0",
        document_id=f"doc_declared_{slug(source.id)}",
        document_type="declared_file_source",
        request_context=request_context,
        source_signals=[signal],
        source_statuses=[
            source_status(
                source_id=source.id,
                source_family="project_guidance",
                scope={"path": source.path},
                status="fresh",
                observed_at=observed_at,
                safe_user_message=f"declared file source {source.id} was read",
                visibility="silent",
                policy_reason="declared record fields are mapped metadata only",
            )
        ],
        source_open_targets=[],
        guidance_records=[],
        session_context_uses=[],
        context_cards=[],
    )


def _unavailable(
    source: DeclaredFileSource,
    request_context: RequestContext,
    observed_at: str,
    reason: str,
) -> CoreContractDocument:
    return CoreContractDocument(
        schema_version="teamctx.core_contract_document.v0",
        document_id=f"doc_declared_{slug(source.id)}",
        document_type="declared_file_source",
        request_context=request_context,
        source_signals=[],
        source_statuses=[
            source_status(
                source_id=source.id,
                source_family="project_guidance",
                scope={"path": source.path},
                status="unavailable",
                observed_at=observed_at,
                safe_user_message=reason,
                visibility="warning_when_relevant",
                policy_reason="declared record fields are mapped metadata only",
            )
        ],
        source_open_targets=[],
        guidance_records=[],
        session_context_uses=[],
        context_cards=[],
    )
