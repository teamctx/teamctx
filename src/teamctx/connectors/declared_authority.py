"""Load declared authority from a .teamctx file.

This is the I/O edge for governance declarations. It lives OUTSIDE the pure core. The file
is treated as the consumer's visible declaration set (Delta_P): a consumer only reads
declarations it has access to, so authority over invisible sources never enters here. Real
source freshness is observed upstream; the thin loader takes a declared ``fresh`` flag.
"""

from __future__ import annotations

import json
from pathlib import Path

from teamctx.core.authority import AuthorityDecl


class DeclaredAuthorityError(ValueError):
    """The declared-authority file exists but cannot be read as authority declarations."""


def load_declared_authority(path: Path) -> list[AuthorityDecl]:
    """Read declared authority from ``path``. Returns ``[]`` if the file does not exist.
    A file that exists but is malformed raises ``DeclaredAuthorityError`` (fail closed with a
    plain, fixable message), never a raw traceback."""

    if not path.exists():
        return []
    try:
        raw = path.read_bytes()
    except OSError as exc:
        raise DeclaredAuthorityError(
            f"{path} is not valid teamctx authority JSON ({exc}). Fix or remove the file."
        ) from exc
    return parse_declared_authority_bytes(raw, str(path))


def parse_declared_authority_bytes(raw: bytes, source: str) -> list[AuthorityDecl]:
    try:
        text = raw.decode("utf-8")
    except UnicodeDecodeError as exc:
        raise DeclaredAuthorityError(
            f"{source} is not valid teamctx authority JSON ({exc}). Fix or remove the file."
        ) from exc
    try:
        data = json.loads(text)
    except json.JSONDecodeError as exc:
        raise DeclaredAuthorityError(
            f"{source} is not valid teamctx authority JSON ({exc}). Fix or remove the file."
        ) from exc
    if not isinstance(data, list):
        raise DeclaredAuthorityError(
            f"{source} is not valid teamctx authority JSON (expected a list of declarations). "
            "Fix or remove the file."
        )
    try:
        return [
            AuthorityDecl(
                subject=str(item["subject"]),
                source=str(item["source"]),
                priority=int(item["priority"]),
                value=str(item["value"]),
                fresh=bool(item["fresh"]),
            )
            for item in data
        ]
    except (KeyError, TypeError, ValueError) as exc:
        raise DeclaredAuthorityError(
            f"{source} is not valid teamctx authority JSON (a declaration is missing a field or "
            "has the wrong type). Fix or remove the file."
        ) from exc
