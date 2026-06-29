"""Resolve a token from the environment (value, then a file). Lightweight by design:
no project imports, so the hot hook path can use it without pulling the broker."""

from __future__ import annotations

import os
import subprocess
from pathlib import Path


def resolve_token(token_env: str = "GITHUB_TOKEN") -> str | None:
    """The value of ``token_env`` wins; else the path in ``{token_env}_FILE`` is read. A missing
    or unreadable file yields ``None`` (honest absence, never a crash). So ``resolve_token()``
    reads ``GITHUB_TOKEN`` then ``GITHUB_TOKEN_FILE``, and ``resolve_token("MY_TOKEN")`` reads
    ``MY_TOKEN`` then ``MY_TOKEN_FILE``."""

    token = os.environ.get(token_env)
    if token:
        return token
    token_file = os.environ.get(f"{token_env}_FILE")
    if token_file:
        try:
            return Path(token_file).expanduser().read_text(encoding="utf-8").strip() or None
        except OSError:
            return None
    return None


def resolve_github_token(token_env: str = "GITHUB_TOKEN") -> str | None:
    """``resolve_token`` plus a ``gh auth token`` fallback, but ONLY on the default
    ``GITHUB_TOKEN`` path. A custom ``token_env`` stays env then file only, so the existing
    'force the no-token path with a custom unset env var' behavior is preserved. The ``gh`` step
    is also skipped when ``TEAMCTX_DISABLE_GH_AUTH`` is set (test isolation)."""

    token = resolve_token(token_env)
    if token:
        return token
    if token_env != "GITHUB_TOKEN":
        return None
    if os.environ.get("TEAMCTX_DISABLE_GH_AUTH"):
        return None
    return _gh_auth_token()


def _gh_auth_token() -> str | None:
    try:
        result = subprocess.run(
            ["gh", "auth", "token"],
            capture_output=True,
            text=True,
            check=True,
            timeout=5,
        )
    except (OSError, subprocess.CalledProcessError, subprocess.TimeoutExpired):
        return None
    return result.stdout.strip() or None
