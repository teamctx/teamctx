"""Load declared authority from a .teamctx file.

This is the I/O edge for governance declarations. It lives OUTSIDE the pure core. The file
is treated as the consumer's visible declaration set (Delta_P): a consumer only reads
declarations it has access to, so authority over invisible sources never enters here. Real
source freshness is observed upstream; the thin loader takes a declared ``fresh`` flag.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any, cast

from teamctx.core.authority import AuthorityDecl


def load_declared_authority(path: Path) -> list[AuthorityDecl]:
    """Read declared authority from ``path``. Returns ``[]`` if the file does not exist."""

    if not path.exists():
        return []
    data = cast("list[dict[str, Any]]", json.loads(path.read_text(encoding="utf-8")))
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
