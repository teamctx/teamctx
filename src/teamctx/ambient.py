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
from typing import TYPE_CHECKING, Any, Literal, cast

from teamctx import __version__

if TYPE_CHECKING:  # keep the module import-light on the no-op path (P2-2): lazy at runtime
    from teamctx.core.broker import BrokerAnswer
    from teamctx.core.contracts import (
        ContextCard,
        CoreContractDocument,
        RequestContext,
        SourceFamily,
        SourceSignal,
    )

AnswerClass = Literal["GOOD", "GAP-KNOWN", "NONE"]
Decision = Literal["speak_full", "silent", "recheck_due"]

# Bumped from v1: closure content identity now flows through an explicit projection seam, so
# older baselines are re-grounded once under the new schema.
_STATE_SCHEMA_VERSION = "teamctx.ambient_state.v2"
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


DeltaDirection = Literal["appear", "disappear", "transition", "coverage_shrank"]


@dataclass(frozen=True)
class Delta:
    """One thing that changed since the session's baseline for this key. ``identity`` carries the
    finding for appear/disappear (and is a sentinel for the whole-check transition/shrank, which the
    render reads off the current world). ``note`` carries a coverage-shrank reason."""

    direction: DeltaDirection
    check: str
    identity: FindingMaterial
    note: str | None = None


# A check is "verifiable" when it reached a real answer, a "gap" when it could not be confirmed.
_VERIFIED_STATUSES: frozenset[str] = frozenset({"clear", "found"})
_GAP_STATUSES: frozenset[str] = frozenset({"unreachable", "pending", "unbounded"})


def compute_deltas(old: BaselineMaterial | None, new: BaselineMaterial) -> tuple[Delta, ...]:
    """What changed from ``old`` to ``new``, per check, as ordered ``Delta`` records.

    Last-value semantics by construction: the baseline holds only the last observed material, so a
    finding that leaves and returns diffs as a disappearance and then a fresh appearance (the
    reopened-PR re-speak). No baseline (first grounding) yields no deltas: nothing has changed since
    a start that just happened."""

    if old is None:
        return ()
    old_by_check = {check.check: check for check in old.checks}
    deltas: list[Delta] = []
    for new_check in new.checks:
        old_check = old_by_check.get(new_check.check) or CheckMaterial(
            check=new_check.check, status=""
        )
        deltas.extend(_check_deltas(old_check, new_check))
    return tuple(deltas)


def _check_deltas(old: CheckMaterial, new: CheckMaterial) -> tuple[Delta, ...]:
    if old.status in _GAP_STATUSES and new.status in _VERIFIED_STATUSES:
        # a gap closed: the source is back. The render reads the current world for the clear phrase
        # or the finding line, so the whole-check transition is one voice (no separate appear).
        return (Delta("transition", new.check, _sentinel_identity(new.check)),)
    if old.status in _VERIFIED_STATUSES and new.status == "unreachable":
        # coverage shrank: what could be verified no longer can.
        return (Delta("coverage_shrank", new.check, _sentinel_identity(new.check), note=new.note),)
    old_by_key = {finding.key: finding for finding in old.findings}
    new_by_key = {finding.key: finding for finding in new.findings}
    deltas: list[Delta] = []
    for key, finding in new_by_key.items():
        if key not in old_by_key:
            deltas.append(Delta("appear", new.check, finding))
    for key, finding in old_by_key.items():
        if key not in new_by_key:
            deltas.append(Delta("disappear", new.check, finding))
    return tuple(deltas)


def _sentinel_identity(check: str) -> FindingMaterial:
    return FindingMaterial(key=f"{check}:__source__")


# Which source family a delta about each check belongs to, so the minted signal is well-formed.
_DELTA_FAMILY: dict[str, SourceFamily] = {
    "conflict": "git_hosting",
    "criteria": "issue_tracker",
    "docs": "docs",
    "gate": "ci_deploy",
}
_DELTA_DIRECTIONS: frozenset[str] = frozenset(
    {"appear", "disappear", "transition", "coverage_shrank"}
)


def build_delta_document(
    request: RequestContext, deltas: Iterable[Delta], *, observed_at: str
) -> CoreContractDocument:
    """Mint the edge delta document: one ``changed_since_start`` signal per delta, for the broker to
    compose beside the real connector documents. These carry NO CardKind, so they never derive a
    card, verdict, or closure entry; the kind stays the current world. The assessment reads them
    back with ``deltas_from_signals``."""

    from teamctx.core.contracts import CoreContractDocument

    signals = [
        _delta_signal(delta, request=request, observed_at=observed_at, index=index)
        for index, delta in enumerate(deltas)
    ]
    return CoreContractDocument(
        schema_version="teamctx.core_contract_document.v0",
        document_id="doc_ambient_delta",
        document_type="ambient_delta",
        request_context=request,
        source_signals=signals,
        source_statuses=[],
        source_open_targets=[],
        guidance_records=[],
        session_context_uses=[],
        context_cards=[],
    )


def _delta_signal(
    delta: Delta, *, request: RequestContext, observed_at: str, index: int
) -> SourceSignal:
    from teamctx.connectors._contract import metadata_only_policy
    from teamctx.core.contracts import SourceSignal

    scope: dict[str, Any] = {
        "delta_check": delta.check,
        "delta_direction": delta.direction,
        "delta_key": delta.identity.key,
        "delta_source_display": delta.identity.source_display,
        "delta_paths": list(delta.identity.paths),
        "delta_gate": delta.identity.gate,
        "delta_detail": delta.identity.detail,
        "delta_doc": delta.identity.doc,
        "delta_superseded_by": delta.identity.superseded_by,
        "delta_note": delta.note or "",
        "reason_code": f"delta.{delta.check}.{delta.direction}",
    }
    return SourceSignal(
        schema_version="teamctx.source_signal.v0",
        id=f"sig_delta_{delta.check}_{delta.direction}_{index}",
        signal_type="changed_since_start",
        source_family=_DELTA_FAMILY.get(delta.check, "local_workspace"),
        scope=scope,
        evidence_summary=f"{delta.check} {delta.direction} since work start",
        source_display=delta.identity.source_display or delta.check,
        freshness="fresh",
        confidence="high",
        visibility="visible",
        created_at=observed_at,
        observed_at=observed_at,
        expires_at="next_refresh",
        policy=metadata_only_policy(
            "delta is derived at the edge; source bodies are not included"
        ),
    )


def deltas_from_signals(signals: Iterable[SourceSignal]) -> tuple[Delta, ...]:
    """Read the deltas back out of the composed answer's ``changed_since_start`` signals, so the
    assessment lane and the render can speak them without re-diffing. The inverse of the minting
    above; the scope schema is defined once, here."""

    deltas: list[Delta] = []
    for signal in signals:
        if signal.signal_type != "changed_since_start":
            continue
        scope = signal.scope
        direction = str(scope.get("delta_direction", ""))
        if direction not in _DELTA_DIRECTIONS:
            continue
        paths_raw = scope.get("delta_paths")
        paths = tuple(str(path) for path in paths_raw) if isinstance(paths_raw, list) else ()
        note = scope.get("delta_note")
        identity = FindingMaterial(
            key=str(scope.get("delta_key", "")),
            source_display=str(scope.get("delta_source_display", "")),
            paths=paths,
            gate=str(scope.get("delta_gate", "")),
            detail=str(scope.get("delta_detail", "")),
            doc=str(scope.get("delta_doc", "")),
            superseded_by=str(scope.get("delta_superseded_by", "")),
        )
        deltas.append(
            Delta(
                direction=cast("DeltaDirection", direction),
                check=str(scope.get("delta_check", "")),
                identity=identity,
                note=str(note) if note else None,
            )
        )
    return tuple(deltas)


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


def _identity_fields(check: str) -> tuple[str, ...]:
    from teamctx.core.kinds import CHECKS_BY_ID

    if check not in CHECKS_BY_ID:
        return ()
    return CHECKS_BY_ID[check].identity.key_scope_fields


def _material_fields(check: str) -> tuple[str, ...]:
    from teamctx.core.kinds import CHECKS_BY_ID

    if check not in CHECKS_BY_ID:
        return ()
    return CHECKS_BY_ID[check].identity.material_scope_fields


def finding_key(check: str, scope: Mapping[str, Any]) -> str:
    """The stable identity key for a finding of ``check``, from the same scope field a signal and
    its card both carry, so the extractor and the bullet suppression agree by construction."""

    fields = _identity_fields(check)
    if len(fields) == 1:
        return f"{check}:{scope.get(fields[0])}"
    if fields:
        parts = [f"{field}={scope.get(field)!r}" for field in fields]
        return f"{check}:{'|'.join(parts)}"
    return f"{check}:None"


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
    material_fields = _material_fields(check)
    paths = (
        tuple(str(path) for path in files)
        if "files" in material_fields and isinstance(files, list)
        else ()
    )
    return FindingMaterial(
        key=finding_key(check, scope),
        source_display=card.source_display,
        paths=paths,
        gate=str(scope.get("gate", "")) if "gate" in _identity_fields(check) else "",
        detail=card.text if check == "criteria" else "",
        doc=str(scope.get("doc", "")) if "doc" in _identity_fields(check) else "",
        superseded_by=(
            str(scope.get("superseded_by", "")) if "superseded_by" in material_fields else ""
        ),
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
