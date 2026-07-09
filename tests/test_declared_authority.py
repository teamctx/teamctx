"""Loading declared authority from a .teamctx file (the consumer's Delta_P declaration set)."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from teamctx.connectors.declared_authority import DeclaredAuthorityError, load_declared_authority
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


def test_invalid_json_raises_plain_error(tmp_path: Path) -> None:
    path = tmp_path / "authority.json"
    path.write_text("{not json", encoding="utf-8")
    with pytest.raises(DeclaredAuthorityError) as excinfo:
        load_declared_authority(path)
    assert "authority.json" in str(excinfo.value)
    assert "not valid" in str(excinfo.value)
    assert "Fix or remove" in str(excinfo.value)


def test_non_list_top_level_raises(tmp_path: Path) -> None:
    path = tmp_path / "authority.json"
    path.write_text('{"subject": "x"}', encoding="utf-8")
    with pytest.raises(DeclaredAuthorityError):
        load_declared_authority(path)


def test_missing_key_raises(tmp_path: Path) -> None:
    path = tmp_path / "authority.json"
    path.write_text('[{"subject": "x"}]', encoding="utf-8")
    with pytest.raises(DeclaredAuthorityError):
        load_declared_authority(path)


def test_non_dict_item_raises(tmp_path: Path) -> None:
    path = tmp_path / "authority.json"
    path.write_text('["x"]', encoding="utf-8")
    with pytest.raises(DeclaredAuthorityError):
        load_declared_authority(path)


def test_unreadable_file_raises(tmp_path: Path) -> None:
    path = tmp_path / "authority.json"
    path.mkdir()
    with pytest.raises(DeclaredAuthorityError):
        load_declared_authority(path)
