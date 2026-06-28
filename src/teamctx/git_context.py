"""Read-only git detection for work-start input resolution.

Resolves the two facts git already knows about a working tree: the repository identity
(owner/name from the ``origin`` remote) and the current branch. Any failure returns ``None``
(honest absence), never a guess, so a non-git or unreachable tree degrades to the broker's
honest-UNKNOWN rather than a fabricated value. No network I/O.
"""

from __future__ import annotations

import subprocess
from pathlib import Path


def detect_repo(root: Path) -> str | None:
    """``owner/name`` of the ``origin`` remote at ``root``, or ``None`` if undeterminable."""

    url = _run_git(root, "remote", "get-url", "origin")
    if url is None:
        return None
    return parse_owner_name(url)


def detect_branch(root: Path) -> str | None:
    """Current branch at ``root``, or ``None`` for detached HEAD or non-git."""

    branch = _run_git(root, "rev-parse", "--abbrev-ref", "HEAD")
    if branch is None or branch == "HEAD":  # "HEAD" means detached
        return None
    return branch


def parse_owner_name(url: str) -> str | None:
    """Extract ``owner/name`` from a git remote URL (scp-style, ssh://, or https)."""

    s = url.strip()
    if s.endswith(".git"):
        s = s[:-4]
    s = s.rstrip("/")
    if "://" in s:
        after_scheme = s.split("://", 1)[1]
        rest = after_scheme.split("/", 1)[1] if "/" in after_scheme else ""
    elif ":" in s:
        rest = s.split(":", 1)[1]
    else:
        return None
    segments = [part for part in rest.strip("/").split("/") if part]
    if len(segments) >= 2:
        return "/".join(segments[-2:])
    return None


def _run_git(root: Path, *args: str) -> str | None:
    try:
        result = subprocess.run(
            ["git", "-C", str(root), *args],
            capture_output=True,
            text=True,
            check=True,
            timeout=10,
        )
    except (OSError, subprocess.CalledProcessError, subprocess.TimeoutExpired):
        return None
    output = result.stdout.strip()
    return output or None
