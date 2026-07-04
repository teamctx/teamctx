"""Per-session ambient baselines for the Claude Code hook.

The hook owns ambient state at the edge. This module stays intentionally import-light: no
connectors, no onboard flow, just local JSON state, cache-key construction, and the silence law.
"""

from __future__ import annotations

import contextlib
import hashlib
import json
import os
import subprocess
import tempfile
from collections.abc import Iterable, Mapping
from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import TYPE_CHECKING, Any, Literal

from teamctx import __version__

if TYPE_CHECKING:  # keep the module import-light on the no-op path (P2-2): lazy at runtime
    from teamctx.core.broker import BrokerAnswer
    from teamctx.core.contracts import ContextCard

AnswerClass = Literal["GOOD", "GAP-KNOWN", "NONE"]
Decision = Literal["speak_full", "silent", "recheck_due"]

# Bumped from v0: a baseline now carries the per-check delta material beside the digest, so any
# v0 file is a different shape and is read as no-baseline (the corrupt-is-NONE path covers it).
_STATE_SCHEMA_VERSION = "teamctx.ambient_state.v1"
_DEFAULT_INTERVAL_SECONDS = 90
_MIN_INTERVAL_SECONDS = 30
_RESTATEMENT_FLOOR_SECONDS = 900
_EVICT_AFTER_SECONDS = 7 * 24 * 60 * 60
_AMBIENT_IGNORE_STANZA = (
    "# teamctx ambient state (local)\n"
    ".teamctx/ambient/\n"
)


@dataclass(frozen=True)
class FindingMaterial:
    """One finding's stable identity, captured so a later run can say EXACTLY what appeared or
    left ("PR #7 appeared, touching src/app.py"). Only source_display and the check-specific
    identity fields; never evidence prose beyond what a delta line needs."""

    key: str
    source_display: str = ""
    paths: tuple[str, ...] = ()
    gate: str = ""
    detail: str = ""
    doc: str = ""
    superseded_by: str = ""


@dataclass(frozen=True)
class CheckMaterial:
    """One check's delta material: its current status plus the identities of its findings."""

    check: str
    status: str
    note: str | None = None
    findings: tuple[FindingMaterial, ...] = ()


@dataclass(frozen=True)
class BaselineMaterial:
    """The delta material for a whole answer: one entry per check, in check order."""

    checks: tuple[CheckMaterial, ...] = ()


@dataclass(frozen=True)
class Baseline:
    key: str
    content_digest: str
    class_of_answer: AnswerClass
    last_network_check_at: float
    last_spoken_at: float
    material: BaselineMaterial = field(default_factory=BaselineMaterial)


def ambient_state_dir(project_root: Path) -> Path:
    override = os.environ.get("TEAMCTX_AMBIENT_STATE")
    return Path(override) if override else project_root / ".teamctx" / "ambient"


def ambient_interval_seconds() -> int:
    raw = os.environ.get("TEAMCTX_AMBIENT_INTERVAL_SECONDS")
    try:
        value = int(raw) if raw is not None else _DEFAULT_INTERVAL_SECONDS
    except ValueError:
        value = _DEFAULT_INTERVAL_SECONDS
    return max(_MIN_INTERVAL_SECONDS, value)


def compute_key(
    *,
    repo: str,
    forge: str,
    branch: str | None,
    paths: Iterable[str],
    issues: Iterable[str],
    since: str | None,
    docs_root: str | None,
    profile: str,
    token_present: bool,
    config_bytes: bytes,
    authority_bytes: bytes,
    version: str = __version__,
) -> str:
    config_authority_digest = hashlib.sha256(config_bytes + authority_bytes).hexdigest()
    payload = {
        "repo": repo,
        "forge": forge,
        "branch": branch,
        "paths": sorted({_normalize_path(path) for path in paths if _normalize_path(path)}),
        "issues": sorted(set(issues)),
        "since": since,
        "docs_root": docs_root,
        "profile": profile,
        "token_present": token_present,
        "config_authority_digest": config_authority_digest,
        "version": version,
    }
    canonical = json.dumps(payload, sort_keys=True, separators=(",", ":"))
    return hashlib.sha256(canonical.encode("utf-8")).hexdigest()


def load_baseline(state_dir: Path, session_id: str, key: str) -> Baseline | None:
    state = _read_state(_state_path(state_dir, session_id))
    if state is None:
        return None
    data = state.get(key)
    if not isinstance(data, dict):
        return None
    return _baseline_from_json(key, data)


def store_baseline(
    state_dir: Path,
    session_id: str,
    baseline: Baseline,
    *,
    now: float,
    project_root: Path | None = None,
) -> None:
    state_dir.mkdir(parents=True, exist_ok=True)
    if project_root is not None:
        _ensure_ambient_ignored(project_root, state_dir)
    _evict_old_files(state_dir, now=now)

    path = _state_path(state_dir, session_id)
    state = _read_state(path) or {}
    state[baseline.key] = asdict(baseline)
    payload = {
        "schema_version": _STATE_SCHEMA_VERSION,
        "session_id": session_id,
        "baselines": state,
    }
    text = json.dumps(payload, sort_keys=True, separators=(",", ":")) + "\n"
    _atomic_write(path, text, mode=0o600)


def decide(
    baseline: Baseline | None,
    *,
    now: float,
    interval: int,
    content_digest: str,
    class_of_answer: AnswerClass,
) -> Decision:
    if baseline is None or baseline.class_of_answer == "NONE":
        return "speak_full"

    effective_interval = max(_MIN_INTERVAL_SECONDS, interval)
    if class_of_answer != "NONE" and (
        content_digest != baseline.content_digest or class_of_answer != baseline.class_of_answer
    ):
        return "speak_full"

    if now - baseline.last_network_check_at < effective_interval:
        return "silent"

    if class_of_answer == "NONE":
        return "recheck_due"

    if (
        class_of_answer == "GAP-KNOWN"
        and now - baseline.last_spoken_at >= max(_RESTATEMENT_FLOOR_SECONDS, effective_interval)
    ):
        return "speak_full"
    return "silent"


# The scope field that carries each check's finding identity, so one PR/issue/doc/gate is the
# SAME finding across runs (a re-appearing PR keeps its identity; last-value dedup rides on this).
_FINDING_KEY_FIELD: dict[str, str] = {
    "conflict": "pr_number",
    "criteria": "issue",
    "docs": "doc",
    "gate": "gate",
}


def finding_key(check: str, scope: Mapping[str, Any]) -> str:
    """The stable identity key for a finding of ``check``, from the same scope field a signal and
    its card both carry, so the extractor and the bullet suppression agree by construction."""

    key_field = _FINDING_KEY_FIELD.get(check)
    value = scope.get(key_field) if key_field is not None else None
    return f"{check}:{value}"


def compute_baseline_material(answer: BrokerAnswer) -> BaselineMaterial:
    """Distill a broker answer into per-check delta material: each check's status and the
    identities of its current findings. Delta (``changed_since_start``) signals never enter this:
    it is derived from the assessment, whose kind is the current world (P1-1 keeps silence
    reachable)."""

    from teamctx.assessment import assess  # lazy: the no-op path must not import the core

    assessment = assess(answer)
    checks = tuple(
        CheckMaterial(
            check=state.check,
            status=state.status,
            note=state.note,
            findings=tuple(_finding_material(state.check, card) for card in state.cards),
        )
        for state in assessment.checks
    )
    return BaselineMaterial(checks=checks)


def _finding_material(check: str, card: ContextCard) -> FindingMaterial:
    scope = card.scope
    files = scope.get("files")
    paths = tuple(str(path) for path in files) if check == "conflict" and isinstance(files, list) \
        else ()
    return FindingMaterial(
        key=finding_key(check, scope),
        source_display=card.source_display,
        paths=paths,
        gate=str(scope.get("gate", "")) if check == "gate" else "",
        detail=card.text if check == "criteria" else "",
        doc=str(scope.get("doc", "")) if check == "docs" else "",
        superseded_by=str(scope.get("superseded_by", "")) if check == "docs" else "",
    )


def _material_from_json(data: Any) -> BaselineMaterial:
    if not isinstance(data, dict):
        return BaselineMaterial()
    checks_raw = data.get("checks")
    if not isinstance(checks_raw, list):
        raise ValueError("baseline material: checks must be a list")
    checks: list[CheckMaterial] = []
    for check_data in checks_raw:
        if not isinstance(check_data, dict):
            raise ValueError("baseline material: each check must be an object")
        findings = tuple(
            FindingMaterial(
                key=str(finding["key"]),
                source_display=str(finding.get("source_display", "")),
                paths=tuple(str(path) for path in (finding.get("paths") or ())),
                gate=str(finding.get("gate", "")),
                detail=str(finding.get("detail", "")),
                doc=str(finding.get("doc", "")),
                superseded_by=str(finding.get("superseded_by", "")),
            )
            for finding in check_data.get("findings", [])
        )
        checks.append(
            CheckMaterial(
                check=str(check_data["check"]),
                status=str(check_data["status"]),
                note=check_data.get("note"),
                findings=findings,
            )
        )
    return BaselineMaterial(checks=tuple(checks))


def _read_state(path: Path) -> dict[str, dict[str, Any]] | None:
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return None
    if not isinstance(data, dict):
        return None
    if data.get("schema_version") != _STATE_SCHEMA_VERSION:
        return None
    baselines = data.get("baselines")
    if not isinstance(baselines, dict):
        return None
    if not all(
        isinstance(key, str) and isinstance(value, dict) for key, value in baselines.items()
    ):
        return None
    return baselines


def _baseline_from_json(key: str, data: dict[str, Any]) -> Baseline | None:
    try:
        baseline = Baseline(
            key=data["key"],
            content_digest=data["content_digest"],
            class_of_answer=data["class_of_answer"],
            last_network_check_at=float(data["last_network_check_at"]),
            last_spoken_at=float(data["last_spoken_at"]),
            material=_material_from_json(data.get("material")),
        )
    except (KeyError, TypeError, ValueError):
        return None
    if baseline.key != key:
        return None
    if baseline.class_of_answer not in {"GOOD", "GAP-KNOWN", "NONE"}:
        return None
    return baseline


def _state_path(state_dir: Path, session_id: str) -> Path:
    safe = "".join(c for c in session_id if c.isalnum() or c in "-_")
    return state_dir / f"{safe or 'session'}.json"


def _normalize_path(path: str) -> str:
    normalized = str(path).replace("\\", "/").strip()
    while normalized.startswith("./"):
        normalized = normalized[2:]
    return normalized.strip("/")


def _evict_old_files(state_dir: Path, *, now: float) -> None:
    cutoff = now - _EVICT_AFTER_SECONDS
    for path in state_dir.glob("*.json"):
        with contextlib.suppress(OSError):
            if path.stat().st_mtime < cutoff:
                path.unlink()


def _ensure_ambient_ignored(project_root: Path, state_dir: Path) -> None:
    rel_probe = _relative_probe_path(project_root, state_dir)
    if rel_probe is None or not _is_git_repo(project_root):
        return
    if _is_ignored(project_root, rel_probe):
        return
    gitignore = project_root / ".gitignore"
    existing = gitignore.read_text(encoding="utf-8") if gitignore.exists() else ""
    if ".teamctx/ambient/" in existing:
        return
    prefix = existing if existing == "" or existing.endswith("\n") else existing + "\n"
    _atomic_write(gitignore, prefix + "\n" + _AMBIENT_IGNORE_STANZA)


def _relative_probe_path(project_root: Path, state_dir: Path) -> str | None:
    try:
        rel = (state_dir / "probe.json").relative_to(project_root)
    except ValueError:
        return None
    return rel.as_posix()


def _is_git_repo(root: Path) -> bool:
    try:
        result = subprocess.run(
            ["git", "-C", str(root), "rev-parse", "--is-inside-work-tree"],
            capture_output=True,
            text=True,
        )
    except OSError:
        return False
    return result.returncode == 0


def _is_ignored(root: Path, rel_path: str) -> bool:
    try:
        result = subprocess.run(
            ["git", "-C", str(root), "check-ignore", "--no-index", rel_path],
            capture_output=True,
            text=True,
        )
    except OSError:
        return False
    return result.returncode == 0


def _atomic_write(path: Path, text: str, *, mode: int | None = None) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    final_mode = mode if mode is not None else (_existing_mode(path) or 0o644)
    fd, tmp_name = tempfile.mkstemp(dir=path.parent, prefix=path.name, suffix=".tmp")
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as handle:
            handle.write(text)
        os.chmod(tmp_name, final_mode)
        os.replace(tmp_name, path)
        os.chmod(path, final_mode)
    except BaseException:
        with contextlib.suppress(OSError):
            os.unlink(tmp_name)
        raise


def _existing_mode(path: Path) -> int | None:
    try:
        return path.stat().st_mode & 0o777
    except OSError:
        return None
