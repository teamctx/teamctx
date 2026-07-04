"""``teamctx-hook``: the Claude Code PreToolUse reflex.

On every Edit/Write/MultiEdit event it consults a per-session ambient baseline. The hook re-checks
no more often than the configured interval for a stable key, speaks again when the current answer
changes or a known gap needs re-stating, and otherwise stays quiet. It NEVER blocks an edit and
never crashes the session: any error returns quietly (exit 0) with nothing surfaced.
"""

from __future__ import annotations

import contextlib
import json
import subprocess
import sys
import time
from dataclasses import dataclass, field, replace
from pathlib import Path
from typing import TYPE_CHECKING, Literal

from teamctx.ambient import (
    AnswerClass,
    Baseline,
    BaselineMaterial,
    ambient_interval_seconds,
    ambient_state_dir,
    compute_key,
    decide,
    load_baseline,
    store_baseline,
)
from teamctx.assessment import assess, class_of_answer
from teamctx.clock import utc_now_iso
from teamctx.core.content_digest import content_digest
from teamctx.git_context import repo_relative_path, resolve_project_root

_EDIT_TOOLS = {"Edit", "Write", "MultiEdit"}
_CONFIG_PATH = Path(".teamctx/config.json")
_AUTHORITY_PATH = Path(".teamctx/authority.json")

if TYPE_CHECKING:
    from teamctx.runner import WorkStartInputs


@dataclass(frozen=True)
class Grounding:
    text: str
    content_digest: str
    class_of_answer: AnswerClass
    material: BaselineMaterial = field(default_factory=BaselineMaterial)
    has_deltas: bool = False


def main() -> None:
    # Suppress BaseException, not just Exception: SystemExit/KeyboardInterrupt would otherwise
    # escape, exit non-zero, and let Claude Code block the edit. This is a short-lived hook
    # subprocess, so swallowing them and exiting 0 is correct: a hook must never crash the session.
    with contextlib.suppress(BaseException):  # fail-safe: stay silent, allow the edit
        _run()


def _run() -> None:
    raw = sys.stdin.read()
    if not raw.strip():
        return
    event = json.loads(raw)
    if event.get("hook_event_name") != "PreToolUse" or event.get("tool_name") not in _EDIT_TOOLS:
        return
    file_path = event.get("tool_input", {}).get("file_path")
    cwd = event.get("cwd")
    session_id = event.get("session_id")
    if not file_path or not cwd or not session_id:
        return
    root = resolve_project_root(start=Path(cwd))
    rel_file, inputs, token_present = _prepare_grounding(root, file_path)
    key = _key_for_inputs(root, inputs, token_present=token_present)
    state_dir = ambient_state_dir(root)
    interval = ambient_interval_seconds()
    now = _now_seconds()
    baseline = load_baseline(state_dir, session_id, key)
    if baseline is not None:
        precheck = decide(
            baseline,
            now=now,
            interval=interval,
            content_digest=baseline.content_digest,
            class_of_answer="NONE",
        )
        if precheck == "silent":
            return

    grounding = _ground(root, rel_file, inputs, token_present, baseline)  # broker imported lazily
    # A delta always speaks: it means the pre-delta content changed, so decide() already returns
    # speak_full; has_deltas makes the transition-speak-over-silence law explicit in code.
    should_speak = grounding.has_deltas or baseline is None or decide(
        baseline,
        now=now,
        interval=interval,
        content_digest=grounding.content_digest,
        class_of_answer=grounding.class_of_answer,
    ) == "speak_full"

    store_baseline(
        state_dir,
        session_id,
        Baseline(
            key=key,
            content_digest=grounding.content_digest,
            class_of_answer=grounding.class_of_answer,
            last_network_check_at=now,
            last_spoken_at=(
                now
                if should_speak and grounding.text
                else baseline.last_spoken_at if baseline is not None else now
            ),
            material=grounding.material,
        ),
        now=now,
        project_root=root,
    )
    if should_speak and grounding.text:
        _emit(grounding.text, "PreToolUse")


def _emit(text: str, event_name: Literal["PreToolUse", "UserPromptSubmit"]) -> None:
    print(json.dumps(
        {"hookSpecificOutput": {"hookEventName": event_name, "additionalContext": text}}
    ))


def _changed_paths(root: Path) -> list[str]:
    try:
        result = subprocess.run(
            ["git", "-C", str(root), "status", "--porcelain"],
            capture_output=True, text=True, check=True, timeout=10,
        )
    except (OSError, subprocess.SubprocessError):
        return []
    paths: list[str] = []
    for line in result.stdout.splitlines():
        name = line[3:].strip()
        if " -> " in name:  # rename
            name = name.split(" -> ", 1)[1]
        name = name.strip('"')
        if name:
            paths.append(name)
    return paths


def _prepare_grounding(root: Path, file_path: str) -> tuple[str, WorkStartInputs, bool]:
    from teamctx.resolve import resolve_work_start_inputs
    from teamctx.tokens import resolve_github_token, resolve_token

    rel_file = repo_relative_path(root, file_path)
    github_token = resolve_github_token()
    paths = tuple(dict.fromkeys([rel_file, *_changed_paths(root)]))  # dedup, order-preserving
    inputs = replace(
        resolve_work_start_inputs(paths=paths, token=github_token, root=root),
        profile="reflex",
    )
    if inputs.forge == "gitlab":
        token_present = resolve_token("GITLAB_TOKEN") is not None
    else:
        token_present = github_token is not None
    return rel_file, inputs, token_present


def _key_for_inputs(root: Path, inputs: WorkStartInputs, *, token_present: bool) -> str:
    return compute_key(
        repo=inputs.repo,
        forge=inputs.forge,
        branch=inputs.branch,
        paths=inputs.paths,
        issues=inputs.issues,
        since=inputs.since,
        docs_root=inputs.docs_root,
        profile=inputs.profile,
        token_present=token_present,
        config_bytes=_read_bytes(root / _CONFIG_PATH),
        authority_bytes=_read_bytes(root / _AUTHORITY_PATH),
    )


def _read_bytes(path: Path) -> bytes:
    try:
        return path.read_bytes()
    except OSError:
        return b""


def _now_seconds() -> float:
    return time.time()


def _ground(
    root: Path,
    file_path: str,
    inputs: WorkStartInputs,
    token_present: bool,
    baseline: Baseline | None = None,
) -> Grounding:
    import socket

    from teamctx.ambient import build_delta_document, compute_baseline_material, compute_deltas
    from teamctx.connectors.declared_authority import load_declared_authority
    from teamctx.core.broker import broker_answer_from_documents
    from teamctx.hook_signal import hook_signal
    from teamctx.work_start import DEFAULT_AUTHORITY_PATH, ground_work_start

    observed_at = utc_now_iso()
    old_timeout = socket.getdefaulttimeout()
    socket.setdefaulttimeout(8)  # bound every network call so a hung GitHub never freezes the edit
    try:
        request, documents = ground_work_start(inputs, observed_at=observed_at, project_root=root)
    finally:
        socket.setdefaulttimeout(old_timeout)
    declarations = load_declared_authority(root / DEFAULT_AUTHORITY_PATH)
    base_answer = broker_answer_from_documents(request, documents, declarations)

    material = compute_baseline_material(base_answer)
    deltas = compute_deltas(baseline.material if baseline is not None else None, material)
    if deltas:
        # Compose the SAME documents again with an edge-minted delta document: no second network.
        delta_document = build_delta_document(request, deltas, observed_at=observed_at)
        answer = broker_answer_from_documents(request, [*documents, delta_document], declarations)
    else:
        answer = base_answer

    return Grounding(
        text=hook_signal(answer, file_path=file_path, token_present=token_present),
        content_digest=content_digest(  # over the PRE-DELTA answer; delta signals are excluded
            base_answer.source_signals,
            base_answer.source_statuses,
            base_answer.selection.closure,
            base_answer.selection.authority,
        ),
        class_of_answer=class_of_answer(assess(base_answer)),
        material=material,
        has_deltas=bool(deltas),
    )


if __name__ == "__main__":
    main()
