"""Read-only git detection for work-start input resolution.

Resolves the two facts git already knows about a working tree: the repository identity
(owner/name from the ``origin`` remote) and the current branch. Any failure returns ``None``
(honest absence), never a guess, so a non-git or unreachable tree degrades to the broker's
honest-UNKNOWN rather than a fabricated value. No network I/O.
"""

from __future__ import annotations

import re
import subprocess
from pathlib import Path


def detect_repo(root: Path) -> str | None:
    """``owner/name`` of the ``origin`` remote at ``root`` when it is a github.com remote, else
    ``None`` (honest absence). A non-github origin fails closed: it never becomes a GitHub query."""

    url = _run_git(root, "remote", "get-url", "origin")
    if url is None:
        return None
    return parse_github_repo(url)


def detect_branch(root: Path) -> str | None:
    """Current branch at ``root``, or ``None`` for detached HEAD or non-git."""

    branch = _run_git(root, "rev-parse", "--abbrev-ref", "HEAD")
    if branch is None or branch == "HEAD":  # "HEAD" means detached
        return None
    return branch


_SAFE_SEGMENT = re.compile(r"^[A-Za-z0-9._-]+$")


def parse_github_repo(value: str) -> str | None:
    """Normalize a GitHub repo reference to ``owner/name``. Accepts a bare ``owner/name`` slug
    (github.com by the field's defined meaning) or a github.com URL (https or scp-style ssh).
    Returns ``None`` for a non-github host, the wrong number of path segments, or an unsafe
    segment, so a non-GitHub repo never enters a GitHub-bound path."""

    s = value.strip()
    if s.endswith(".git"):
        s = s[:-4]
    s = s.rstrip("/")
    if "://" in s:  # scheme://[user@]host/owner/name
        after = s.split("://", 1)[1]
        host, _, rest = after.partition("/")
        host = host.rsplit("@", 1)[-1]  # strip optional user@
    elif "@" in s and ":" in s:  # git@host:owner/name (scp-style)
        host, _, rest = s.split("@", 1)[1].partition(":")
    elif ":" in s:  # host:owner/name
        host, _, rest = s.partition(":")
    else:  # bare owner/name slug
        host, rest = None, s
    if host is not None and host != "github.com":
        return None
    segments = [part for part in rest.strip("/").split("/") if part]
    if len(segments) != 2:
        return None
    if any(seg in (".", "..") or not _SAFE_SEGMENT.match(seg) for seg in segments):
        return None
    return "/".join(segments)


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
