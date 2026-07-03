"""Read-only local discovery for work-start inputs.

The issue parser reads local branch names and local commit messages only. Commit messages are
treated as workspace metadata: only closing-keyword issue numbers are extracted, and message text is
never stored, surfaced, or sent to a connector.
"""

from __future__ import annotations

import re
import subprocess
from collections.abc import Iterable
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path

_BRANCH_JIRA_KEY = re.compile(r"(?:^|[/_-])([A-Z][A-Z0-9]+-\d{1,6})(?=[/_-]|$)")
_BRANCH_ISSUE = re.compile(r"(?:^|[/_-])#?(\d{1,6})(?=[/_-]|$)")
_TRAILER_JIRA_KEY = re.compile(
    r"(?:fixes|closes|resolves)\s+([A-Z][A-Z0-9]+-\d{1,6})", re.IGNORECASE
)
_TRAILER_ISSUE = re.compile(r"\b(?:fixes|closes|resolves)\s+#(\d{1,6})\b", re.IGNORECASE)


@dataclass(frozen=True)
class DerivedIssues:
    """Issues derived from local git metadata, with an explicit cap bit for the runner."""

    issues: tuple[tuple[str, str], ...] = ()
    capped: bool = False


def derive_issues(root: Path) -> DerivedIssues:
    """Derive linked issue refs from branch name and local commit trailers.

    Branch provenance wins on a tie. The returned refs are deduped, deterministically sorted, and
    capped at five so the runner can make the cap visible instead of silently omitting extras.
    """

    branch = _current_branch(root)
    if branch is None:
        return DerivedIssues()

    found: dict[str, str] = {}
    for branch_issue in _branch_issue_refs(branch):
        found[branch_issue] = "your branch name"

    merge_base = _merge_base(root)
    if merge_base is not None:
        messages = _run_git(root, "log", "--format=%B", f"{merge_base}..HEAD")
        if messages is not None:
            for trailer_issue in _trailer_issue_refs(messages):
                found.setdefault(trailer_issue, "a commit message trailer")

    capped = len(found) > 5
    issues = tuple((issue, found[issue]) for issue in sorted(found, key=_issue_sort_key)[:5])
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


def _branch_issue_refs(branch: str) -> tuple[str, ...]:
    refs: list[str] = []
    jira_matches = tuple(_BRANCH_JIRA_KEY.finditer(branch))
    refs.extend(match.group(1) for match in jira_matches)
    numeric_source = _remove_spans(
        branch, ((match.start(1), match.end(1)) for match in jira_matches)
    )
    for match in _BRANCH_ISSUE.finditer(numeric_source):
        start = match.start(1)
        if start > 0 and numeric_source[start - 1] in {"v", "V"}:
            continue
        refs.append(f"#{int(match.group(1))}")
        break
    return tuple(refs)


def _trailer_issue_refs(messages: str) -> tuple[str, ...]:
    refs: list[str] = []
    jira_matches = tuple(_TRAILER_JIRA_KEY.finditer(messages))
    refs.extend(match.group(1) for match in jira_matches)
    numeric_source = _remove_spans(
        messages, ((match.start(1), match.end(1)) for match in jira_matches)
    )
    refs.extend(f"#{int(match.group(1))}" for match in _TRAILER_ISSUE.finditer(numeric_source))
    return tuple(refs)


def _remove_spans(text: str, spans: Iterable[tuple[int, int]]) -> str:
    chars = list(text)
    for start, end in spans:
        for index in range(start, end):
            chars[index] = " "
    return "".join(chars)


def _issue_sort_key(issue_ref: str) -> tuple[int, int, str]:
    if issue_ref.startswith("#"):
        try:
            return (0, int(issue_ref[1:]), "")
        except ValueError:
            return (0, 0, issue_ref)
    return (1, 0, issue_ref)


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
