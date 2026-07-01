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
from dataclasses import dataclass
from pathlib import Path

from teamctx.git_context import detect_repo
from teamctx.tokens import resolve_github_token_with_source

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


@dataclass(frozen=True)
class AuthStatus:
    found: bool
    source: str | None
    message: str


def _auth_found_message(token_env: str, source: str | None) -> str:
    if source == "env":
        return f"using {token_env} from your environment."
    if source == "file":
        return f"using the token file in {token_env}_FILE."
    if source == "gh":
        return "using your gh CLI login."
    return "credential found."


def _auth_missing_message(token_env: str) -> str:
    return (
        f"no GitHub credential found. Set {token_env} in your environment (or {token_env}_FILE "
        "with a path to a token file), or run `gh auth login`. Until then teamctx can't check "
        "open PRs or failing checks and will say so, never a false all-clear."
    )


class GithubOnboarder:
    """The one source onboarder today. Host-aware detection reuses Part 1's ``detect_repo``, which
    returns owner/name only for a github.com origin (fail-closed on any other host)."""

    provider = "github"

    def detect(self, root: Path) -> str | None:
        return detect_repo(root)

    def propose_config(self, repo: str) -> dict[str, str]:
        return {"repo": repo}

    def auth_status(self, token_env: str = "GITHUB_TOKEN") -> AuthStatus:
        token, source = resolve_github_token_with_source(token_env)
        if token:
            return AuthStatus(True, source, _auth_found_message(token_env, source))
        return AuthStatus(False, None, _auth_missing_message(token_env))


ONBOARDERS: list[GithubOnboarder] = [GithubOnboarder()]
