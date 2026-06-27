"""``teamctx-hook``: the Claude Code PreToolUse reflex.

On the first Edit/Write/MultiEdit of a session it grounds the agent — runs work_start for the
in-flight change and injects a short signal (ready / heads up / can't verify) as
``additionalContext``. It NEVER blocks an edit and never crashes the session: any error returns
quietly (exit 0) with nothing surfaced. Kept import-light so the per-edit no-op path stays cheap.
"""

from __future__ import annotations

import contextlib
import json
import subprocess
import sys
from datetime import UTC, datetime
from pathlib import Path

_EDIT_TOOLS = {"Edit", "Write", "MultiEdit"}


def main() -> None:
    # Suppress BaseException, not just Exception: SystemExit/KeyboardInterrupt would otherwise
    # escape, exit non-zero, and let Claude Code block the edit. This is a short-lived hook
    # subprocess, so swallowing them and exiting 0 is correct — a hook must never crash the session.
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
    if _already_grounded(session_id):  # once per session — cheap no-op path ends here
        return
    # mark before grounding: on error we stay silent rather than retry every edit
    _mark_grounded(session_id)

    text = _ground(Path(cwd), file_path)  # imports the broker lazily
    if text:
        _emit(text)


def _emit(text: str) -> None:
    print(json.dumps(
        {"hookSpecificOutput": {"hookEventName": "PreToolUse", "additionalContext": text}}
    ))


def _cache_dir() -> Path:
    import os
    import tempfile

    override = os.environ.get("TEAMCTX_HOOK_CACHE")
    base = Path(override) if override else Path(tempfile.gettempdir()) / "teamctx-hook"
    base.mkdir(parents=True, exist_ok=True)
    return base


def _marker(session_id: str) -> Path:
    # safe: Claude Code session ids are UUIDs (hex + '-')
    safe = "".join(c for c in session_id if c.isalnum() or c in "-_")
    return _cache_dir() / f"{safe}.grounded"


def _already_grounded(session_id: str) -> bool:
    return _marker(session_id).exists()


def _mark_grounded(session_id: str) -> None:
    _marker(session_id).write_text("", encoding="utf-8")


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


def _ground(root: Path, file_path: str) -> str:
    from teamctx.hook_signal import hook_signal
    from teamctx.resolve import resolve_work_start_inputs
    from teamctx.tokens import resolve_github_token
    from teamctx.work_start import work_start_answer

    token = resolve_github_token()
    paths = tuple(dict.fromkeys([file_path, *_changed_paths(root)]))  # dedup, order-preserving
    inputs = resolve_work_start_inputs(paths=paths, token=token, root=root)
    answer = work_start_answer(inputs, observed_at=_utc_now(), project_root=root)
    return hook_signal(answer, file_path=file_path, token_present=token is not None)


def _utc_now() -> str:
    return datetime.now(UTC).replace(microsecond=0).isoformat().replace("+00:00", "Z")


if __name__ == "__main__":
    main()
