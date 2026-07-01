"""The onboard command: scaffold a repo for teamctx honestly, over the Part 1 resolvers.

A minimal source-onboarder seam (one GithubOnboarder today, in a plain list) plus the flow that
writes a trackable config, installs the reflex hook, writes an honest CLAUDE.md snippet, reports the
real credential path, and prints a live reachability check. Every write is atomic and idempotent;
the flow returns structured results the CLI renders. No LLM, no verdicts here.
"""

from __future__ import annotations

import contextlib
import os
import tempfile
from pathlib import Path

from teamctx.git_context import detect_repo

# The honest snippet: only what the hook auto-fires today (open PRs on your files, failing checks).
# Do NOT claim changed specs / superseded docs until they auto-fire (the next slice).
CLAUDE_MD_SNIPPET = (
    "## Team context (teamctx)\n"
    "Before you start editing files in this repo, run `teamctx work-start` and factor the result "
    "into your plan. It surfaces open pull requests touching your files and failing checks on your "
    "branch. Tell your human collaborator anything relevant in plain terms so they can decide.\n"
)

# The pre-Phase-3 snippet body, kept verbatim so the upsert can recognize and migrate an old
# unmarked block the user has NOT edited. Never used for new writes.
_LEGACY_SNIPPET_BODY = (
    "## Team context (teamctx)\n"
    "Before you start editing files in this repo, run `teamctx work-start` and factor the result "
    "into your plan. It surfaces open PRs touching your files, failing checks, changed specs, and "
    "superseded docs. Tell your human collaborator anything relevant in plain terms so they can "
    "decide.\n"
)


def _atomic_write(path: Path, text: str) -> None:
    """Write ``text`` to ``path`` atomically: a temp file in the same directory, then rename. A
    crash mid-write never leaves a half-written file at ``path``. The temp file is on the same
    filesystem as the target (``dir=path.parent``), so ``os.replace`` is atomic."""

    path.parent.mkdir(parents=True, exist_ok=True)
    fd, tmp_name = tempfile.mkstemp(dir=path.parent, prefix=path.name, suffix=".tmp")
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as handle:
            handle.write(text)
        os.replace(tmp_name, path)
    except BaseException:
        with contextlib.suppress(OSError):
            os.unlink(tmp_name)
        raise


class GithubOnboarder:
    """The one source onboarder today. Host-aware detection reuses Part 1's ``detect_repo``, which
    returns owner/name only for a github.com origin (fail-closed on any other host)."""

    provider = "github"

    def detect(self, root: Path) -> str | None:
        return detect_repo(root)

    def propose_config(self, repo: str) -> dict[str, str]:
        return {"repo": repo}


ONBOARDERS: list[GithubOnboarder] = [GithubOnboarder()]
