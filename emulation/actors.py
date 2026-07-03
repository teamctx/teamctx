"""Actor and transport scaffolding for the Phase 5 emulation harness.

Everything here runs against LOCAL tmp git repos and the bundled mock server; nothing ever
touches real GitHub/GitLab/Atlassian. The emulated team is keyed on BRANCH and ORDER-OF-
OPERATIONS, never author identity (program spec rev 2, P1-1), so one git identity stages every
role. The synthetic PreToolUse builder emits exactly the fields ``teamctx.hook`` reads, and every
hook invocation gets a FRESH ``session_id`` plus a fresh hook-cache dir so the once-per-session
marker never turns a second run into a silent no-op (the spec's hook-driver trap).
"""

from __future__ import annotations

import json
import os
import subprocess
import sys
import uuid
from collections.abc import Mapping
from dataclasses import dataclass, field
from pathlib import Path

# The disposable lab slug is committed AS-IS (a lab asset, not instance data), matching the spec's
# redaction rule. The mock server ignores owner/name, so any github.com slug routes correctly.
DEFAULT_SLUG = "teamctx-emulation-lab/widgets"
SYNTHETIC_TOKEN = "emulation-operator-token"  # authenticates only to the local mock, never live

_BASE_DATE = "2026-07-01T09:15:00+00:00"
_WORK_DATE = "2026-07-02T10:00:00+00:00"


def _src_root() -> Path:
    """This worktree's ``src`` so subprocess invocations drive THIS branch's teamctx, not
    whatever is pip-installed elsewhere."""

    return Path(__file__).resolve().parent.parent / "src"


def fresh_session_id() -> str:
    """A unique session id per hook invocation, so the once-per-session marker never no-ops."""

    return f"emu-{uuid.uuid4()}"


def _git(root: Path, *args: str, date: str | None = None) -> str:
    env = dict(os.environ)
    if date is not None:
        env["GIT_AUTHOR_DATE"] = date
        env["GIT_COMMITTER_DATE"] = date
    result = subprocess.run(
        ["git", "-C", str(root), *args],
        check=True,
        capture_output=True,
        text=True,
        env=env,
    )
    return result.stdout.strip()


def write_file(root: Path, rel_path: str, text: str) -> None:
    target = root / rel_path
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(text, encoding="utf-8")


@dataclass(frozen=True)
class LabRepo:
    """A local git clone that looks, to teamctx, like a checkout of the lab repo."""

    root: Path
    slug: str
    branch: str


def build_lab_repo(
    root: Path,
    *,
    slug: str = DEFAULT_SLUG,
    branch: str = "feature",
    files: Mapping[str, str] | None = None,
    base_files: Mapping[str, str] | None = None,
    base_date: str = _BASE_DATE,
    work_date: str = _WORK_DATE,
    work_commit: bool = True,
) -> LabRepo:
    """Stage a tmp repo: a dated base commit on ``main`` with an ``origin`` remote and tracking
    refs (so repo/branch auto-detection and the merge-base ``since`` derivation both resolve),
    then a work branch. Mirrors the tmp-repo pattern of tests/test_auto_derivation_e2e.py."""

    root.mkdir(parents=True, exist_ok=True)
    _git(root, "init", "-q", "-b", "main")
    _git(root, "config", "user.email", "operator@emulation.example")
    _git(root, "config", "user.name", "emulation-operator")
    for rel_path, text in (base_files or {"README.md": "base\n"}).items():
        write_file(root, rel_path, text)
    _git(root, "add", ".")
    _git(root, "commit", "-qm", "base", date=base_date)
    _git(root, "remote", "add", "origin", f"git@github.com:{slug}.git")
    _git(root, "update-ref", "refs/remotes/origin/main", "HEAD")
    _git(root, "symbolic-ref", "refs/remotes/origin/HEAD", "refs/remotes/origin/main")
    _git(root, "checkout", "-qb", branch)
    if files:
        for rel_path, text in files.items():
            write_file(root, rel_path, text)
        if work_commit:
            _git(root, "add", ".")
            _git(root, "commit", "-qm", "work", date=work_date)
    return LabRepo(root=root, slug=slug, branch=branch)


@dataclass(frozen=True)
class SubprocessEnv:
    """The env for a CLI/hook subprocess: pinned to this worktree's src and to the mock server,
    with a synthetic token. Even if a real credential is inherited, every GitHub call is bounded to
    the ``TEAMCTX_GITHUB_API_ROOT`` mock, so no live request can escape."""

    api_root: str
    token: str = SYNTHETIC_TOKEN
    hook_cache: Path | None = None
    observed_at: str | None = None

    def as_dict(self) -> dict[str, str]:
        env = dict(os.environ)
        existing = env.get("PYTHONPATH")
        src = str(_src_root())
        env["PYTHONPATH"] = src if not existing else src + os.pathsep + existing
        env["TEAMCTX_GITHUB_API_ROOT"] = self.api_root
        env["TEAMCTX_DISABLE_GH_AUTH"] = "1"
        env.pop("GITHUB_TOKEN_FILE", None)
        if self.token:
            env["GITHUB_TOKEN"] = self.token
        else:
            env.pop("GITHUB_TOKEN", None)
        if self.hook_cache is not None:
            env["TEAMCTX_HOOK_CACHE"] = str(self.hook_cache)
        return env


@dataclass(frozen=True)
class CliRun:
    args: list[str]
    returncode: int
    stdout: str
    stderr: str

    @property
    def output(self) -> str:
        """The reader-facing text (stdout for a report; stderr carries a ClickException)."""

        return self.stdout if self.stdout.strip() else self.stderr


def run_cli(args: list[str], *, cwd: Path, env: SubprocessEnv) -> CliRun:
    """Invoke the REAL CLI as a subprocess (``python -m teamctx.cli``), never in-process, so the
    row exercises the same entrypoint a user runs."""

    proc = subprocess.run(
        [sys.executable, "-m", "teamctx.cli", *args],
        cwd=str(cwd),
        env=env.as_dict(),
        capture_output=True,
        text=True,
    )
    return CliRun(args=args, returncode=proc.returncode, stdout=proc.stdout, stderr=proc.stderr)


def pretooluse_event(
    *,
    cwd: Path,
    file_path: str,
    session_id: str | None = None,
    tool_name: str = "Edit",
) -> dict[str, object]:
    """Build a synthetic PreToolUse event with EXACTLY the fields ``teamctx.hook`` reads:
    ``hook_event_name``, ``tool_name``, ``tool_input.file_path``, ``cwd``, ``session_id``."""

    return {
        "hook_event_name": "PreToolUse",
        "tool_name": tool_name,
        "tool_input": {"file_path": file_path},
        "cwd": str(cwd),
        "session_id": session_id or fresh_session_id(),
    }


def run_hook(event: Mapping[str, object], *, cwd: Path, env: SubprocessEnv) -> str:
    """Drive ``python -m teamctx.hook`` with a synthetic event on stdin and return the injected
    ``additionalContext`` (empty string when the hook stays silent)."""

    proc = subprocess.run(
        [sys.executable, "-m", "teamctx.hook"],
        input=json.dumps(event),
        cwd=str(cwd),
        env=env.as_dict(),
        capture_output=True,
        text=True,
    )
    out = proc.stdout.strip()
    if not out:
        return ""
    data = json.loads(out)
    context = data["hookSpecificOutput"]["additionalContext"]
    return context if isinstance(context, str) else ""


@dataclass
class ClaudeConfig:
    """Placeholder for the agent-driven rows (spec's Actor B with an Opus subagent). The offline
    harness never drives a model; agentic rows are exercised through the deterministic transports.
    Kept so the actor vocabulary matches the spec without implying a live model call."""

    enabled: bool = False
    notes: list[str] = field(default_factory=list)
