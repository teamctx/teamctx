"""Entry point for ``teamctx-mcp`` that fails with a plain message when the optional MCP
dependency is missing, instead of a raw ImportError traceback."""

from __future__ import annotations

import sys


def main() -> None:
    try:
        from teamctx.mcp_server import main as server_main
    except ImportError as exc:
        name = getattr(exc, "name", None) or ""
        if name.split(".")[0] == "mcp":
            print(
                "teamctx-mcp needs the optional MCP dependency, which is not installed. "
                "Install it with: pip install 'teamctx[mcp]'",
                file=sys.stderr,
            )
            raise SystemExit(1) from exc
        raise
    server_main()
