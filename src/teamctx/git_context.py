"""Read-only git detection for work-start input resolution.

Resolves the two facts git already knows about a working tree: the repository identity
(owner/name from the ``origin`` remote) and the current branch. Any failure returns ``None``
(honest absence), never a guess, so a non-git or unreachable tree degrades to the broker's
honest-UNKNOWN rather than a fabricated value. No network I/O.
"""

from __future__ import annotations

import re
import subprocess
from dataclasses import dataclass
from pathlib import Path
from typing import Literal

type ForgeProvider = Literal["github", "gitlab"]


def detect_repo(root: Path) -> str | None:
    """``owner/name`` of the ``origin`` remote at ``root`` when it is a github.com remote, else
    ``None`` (honest absence). A non-github origin fails closed: it never becomes a GitHub query."""

    detected = detect_forge_repo(root)
    if detected is None:
        return None
    slug, forge = detected
    return slug if forge == "github" else None


def detect_forge_repo(root: Path) -> tuple[str, ForgeProvider] | None:
    """Repo slug and forge provider from the ``origin`` remote host, or ``None``.

    Detection is host-gated: github.com becomes ``("owner/name", "github")``; gitlab.com becomes
    ``("group[/sub]/project", "gitlab")``; any other host is honest absence.
    """

    url = _run_git(root, "remote", "get-url", "origin")
    if url is None:
        return None
    ref = _repo_ref(url)
    if ref.host == "github.com":
        slug = parse_github_repo(url)
        return (slug, "github") if slug is not None else None
    if ref.host == "gitlab.com":
        slug = parse_gitlab_repo(url)
        return (slug, "gitlab") if slug is not None else None
    return None


def detect_branch(root: Path) -> str | None:
    """Current branch at ``root``, or ``None`` for detached HEAD or non-git."""

    branch = _run_git(root, "rev-parse", "--abbrev-ref", "HEAD")
    if branch is None or branch == "HEAD":  # "HEAD" means detached
        return None
    return branch


_SAFE_SEGMENT = re.compile(r"^[A-Za-z0-9._-]+$")


@dataclass(frozen=True)
class _RepoRef:
    host: str | None
    rest: str


def parse_github_repo(value: str) -> str | None:
    """Normalize a GitHub repo reference to ``owner/name``. Accepts a bare ``owner/name`` slug
    (github.com by the field's defined meaning) or a github.com URL (https or scp-style ssh).
    Returns ``None`` for a non-github host, the wrong number of path segments, or an unsafe
    segment, so a non-GitHub repo never enters a GitHub-bound path."""

    ref = _repo_ref(value)
    if ref.host is not None and ref.host != "github.com":
        return None
    return _parse_repo_segments(ref.rest, min_segments=2, max_segments=2)


def parse_gitlab_repo(value: str) -> str | None:
    """Normalize a GitLab repo reference.

    Accepts a bare ``group/project`` or ``group/sub/project`` slug (gitlab.com by the field's
    defined meaning), plus gitlab.com URL and scp-style ssh forms. GitLab nested groups are
    preserved; unsafe segments and non-gitlab hosts fail closed.
    """

    ref = _repo_ref(value)
    if ref.host is not None and ref.host != "gitlab.com":
        return None
    return _parse_repo_segments(ref.rest, min_segments=2, max_segments=None)


def _repo_ref(value: str) -> _RepoRef:
    s = value.strip()
    if s.endswith(".git"):
        s = s[:-4]
    s = s.rstrip("/")
    if "://" in s:
        after = s.split("://", 1)[1]
        host, _, rest = after.partition("/")
        host = host.rsplit("@", 1)[-1]
        return _RepoRef(host, rest)
    if "@" in s and ":" in s:
        host, _, rest = s.split("@", 1)[1].partition(":")
        return _RepoRef(host, rest)
    if ":" in s:
        host, _, rest = s.partition(":")
        return _RepoRef(host, rest)
    return _RepoRef(None, s)


def _parse_repo_segments(
    rest: str, *, min_segments: int, max_segments: int | None
) -> str | None:
    segments = [part for part in rest.strip("/").split("/") if part]
    if len(segments) < min_segments:
        return None
    if max_segments is not None and len(segments) > max_segments:
        return None
    if any(seg in (".", "..") or not _SAFE_SEGMENT.match(seg) for seg in segments):
        return None
    return "/".join(segments)


def resolve_project_root(start: Path | None = None, override: Path | None = None) -> Path:
    """The project root every surface agrees on. ``override`` (for example MCP's
    ``TEAMCTX_PROJECT_ROOT``) wins; else the git toplevel of ``start``; else ``start`` itself
    (cwd fallback, so a non-git tree still works). ``start`` defaults to the current directory,
    resolved here rather than as an import-time default argument."""

    if override is not None:
        return override
    base = start if start is not None else Path.cwd()
    toplevel = _git_toplevel(base)
    return toplevel if toplevel is not None else base


def repo_relative_path(root: Path, path: str) -> str:
    """Normalize a caller path to a repo-root-relative POSIX string, so it matches the broker's
    paths (PR changed files, gate files, docs are all repo-relative). An absolute path is made
    relative to the git toplevel; a relative path is resolved against ``root`` and re-expressed
    relative to the toplevel, so './docs/x.md' and 'docs/x.md' agree. If it cannot be made
    repo-relative (no git tree, or a path outside the repo), the input is returned as a clean
    POSIX string rather than raising, so a non-git tree still works."""

    candidate = Path(path)
    toplevel = _git_toplevel(root)
    if toplevel is None:
        return candidate.as_posix()
    absolute = candidate if candidate.is_absolute() else (root / candidate)
    try:
        return absolute.resolve().relative_to(toplevel.resolve()).as_posix()
    except (OSError, ValueError):
        return candidate.as_posix()


def _git_toplevel(root: Path) -> Path | None:
    out = _run_git(root, "rev-parse", "--show-toplevel")
    return Path(out) if out is not None else None


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
