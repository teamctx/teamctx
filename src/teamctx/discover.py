"""Read-only local discovery for work-start inputs.

The issue parser reads local branch names and local commit messages only. Commit messages are
treated as workspace metadata: only closing-keyword issue numbers are extracted, and message text is
never stored, surfaced, or sent to a connector.
"""

from __future__ import annotations

import re
import subprocess
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path

_BRANCH_ISSUE = re.compile(r"(?:^|[/_-])#?(\d{1,6})(?=[/_-]|$)")
_TRAILER_ISSUE = re.compile(r"\b(?:fixes|closes|resolves)\s+#(\d{1,6})\b", re.IGNORECASE)


@dataclass(frozen=True)
class DerivedIssues:
    """Issues derived from local git metadata, with an explicit cap bit for the runner."""

    issues: tuple[tuple[str, str], ...] = ()
    capped: bool = False


def derive_issues(root: Path) -> DerivedIssues:
    """Derive linked issue refs from branch name and local commit trailers.

    Branch provenance wins on a tie. The returned refs are deduped, numerically sorted, and capped
    at five so the runner can make the cap visible instead of silently omitting extras.
    """

    branch = _current_branch(root)
    if branch is None:
        return DerivedIssues()

    found: dict[int, str] = {}
    branch_issue = _branch_issue_number(branch)
    if branch_issue is not None:
        found[branch_issue] = "your branch name"

    merge_base = _merge_base(root)
    if merge_base is not None:
        messages = _run_git(root, "log", "--format=%B", f"{merge_base}..HEAD")
        if messages is not None:
            for match in _TRAILER_ISSUE.finditer(messages):
                issue = int(match.group(1))
                found.setdefault(issue, "a commit message trailer")

    capped = len(found) > 5
    issues = tuple((f"#{issue}", found[issue]) for issue in sorted(found)[:5])
    return DerivedIssues(issues=issues, capped=capped)


def derive_since(root: Path) -> tuple[str, str] | None:
    """Derive the start timestamp from the default-branch merge base."""

    if _current_branch(root) is None:
        return None
    merge_base = _merge_base(root)
    if merge_base is None:
        return None
    raw_timestamp = _run_git(root, "show", "-s", "--format=%cI", merge_base)
    if raw_timestamp is None:
        return None
    try:
        timestamp = _to_utc_iso(raw_timestamp)
    except ValueError:
        return None
    short = _run_git(root, "rev-parse", "--short", merge_base) or merge_base[:7]
    return timestamp, f"when you branched (merge-base {short})"


def _branch_issue_number(branch: str) -> int | None:
    for match in _BRANCH_ISSUE.finditer(branch):
        start = match.start(1)
        if start > 0 and branch[start - 1] in {"v", "V"}:
            continue
        return int(match.group(1))
    return None


def _current_branch(root: Path) -> str | None:
    branch = _run_git(root, "rev-parse", "--abbrev-ref", "HEAD")
    if branch is None or branch == "HEAD":
        return None
    return branch


def _merge_base(root: Path) -> str | None:
    default_branch = _default_branch(root)
    if default_branch is None:
        return None
    return _run_git(root, "merge-base", default_branch, "HEAD")


def _default_branch(root: Path) -> str | None:
    origin_head = _run_git(root, "symbolic-ref", "--short", "refs/remotes/origin/HEAD")
    if origin_head is not None:
        return origin_head
    for candidate in ("origin/main", "origin/master"):
        if _run_git(root, "rev-parse", "--verify", "--quiet", candidate) is not None:
            return candidate
    return None


def _to_utc_iso(value: str) -> str:
    parsed = datetime.fromisoformat(value)
    parsed = parsed.replace(tzinfo=UTC) if parsed.tzinfo is None else parsed.astimezone(UTC)
    return parsed.replace(microsecond=0).isoformat().replace("+00:00", "Z")


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
