"""Loading declared authority from a .teamctx file (the consumer's Delta_P declaration set)."""

from __future__ import annotations

import json
from pathlib import Path

from teamctx.connectors.declared_authority import load_declared_authority
from teamctx.core.authority import AuthorityDecl


def test_absent_file_yields_no_declarations(tmp_path: Path) -> None:
    assert load_declared_authority(tmp_path / "nope.json") == []


def test_loads_declarations_from_json(tmp_path: Path) -> None:
    path = tmp_path / "authority.json"
    path.write_text(
        json.dumps(
            [
                {
                    "subject": "rounding-cap",
                    "source": "confluence:Rounding Policy",
                    "priority": 10,
                    "value": "3",
                    "fresh": True,
                }
            ]
        ),
        encoding="utf-8",
    )
    decls = load_declared_authority(path)
    assert decls == [
        AuthorityDecl(
            subject="rounding-cap",
            source="confluence:Rounding Policy",
            priority=10,
            value="3",
            fresh=True,
        )
    ]
