"""Resolve the GitHub token from the environment (value, then file). Lightweight by design —
no project imports — so the hot hook path can use it without pulling the broker."""

from __future__ import annotations

import os
from pathlib import Path


def resolve_github_token() -> str | None:
    """``GITHUB_TOKEN`` (the value) wins; else ``GITHUB_TOKEN_FILE`` (a path) is read. A missing
    or unreadable file yields ``None`` — honest absence, never a crash."""

    token = os.environ.get("GITHUB_TOKEN")
    if token:
        return token
    token_file = os.environ.get("GITHUB_TOKEN_FILE")
    if token_file:
        try:
            return Path(token_file).expanduser().read_text(encoding="utf-8").strip() or None
        except OSError:
            return None
    return None
