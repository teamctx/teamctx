"""Resolve a token from the environment (value, then a file). Lightweight by design:
no project imports, so the hot hook path can use it without pulling the broker."""

from __future__ import annotations

import os
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
