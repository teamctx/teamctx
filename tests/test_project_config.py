from __future__ import annotations

import json
from pathlib import Path

import pytest

from teamctx.project_config import ProjectConfigError, load_project_config


def test_project_config_rejects_unknown_fields(tmp_path: Path) -> None:
    config_path = tmp_path / "config.json"
    config_path.write_text(
        json.dumps(
            {
                "schema_version": "teamctx.project_config.v0",
                "mine_everything": True,
            }
        ),
        encoding="utf-8",
    )

    with pytest.raises(ProjectConfigError):
        load_project_config(config_path)


def test_project_config_loads_work_start_section(tmp_path: Path) -> None:
    config_path = tmp_path / "config.json"
    config_path.write_text(
        json.dumps(
            {
                "schema_version": "teamctx.project_config.v0",
                "work_start": {"repo": "acme/widgets", "docs_root": "docs"},
            }
        ),
        encoding="utf-8",
    )
    config = load_project_config(config_path)
    assert config.work_start is not None
    assert config.work_start.repo == "acme/widgets"
    assert config.work_start.docs_root == "docs"


def test_project_config_without_work_start_is_none(tmp_path: Path) -> None:
    config_path = tmp_path / "config.json"
    config_path.write_text(
        json.dumps({"schema_version": "teamctx.project_config.v0"}),
        encoding="utf-8",
    )
    config = load_project_config(config_path)
    assert config.work_start is None


def test_work_start_section_rejects_unknown_fields(tmp_path: Path) -> None:
    config_path = tmp_path / "config.json"
    config_path.write_text(
        json.dumps(
            {
                "schema_version": "teamctx.project_config.v0",
                "work_start": {"repo": "acme/widgets", "surprise": True},
            }
        ),
        encoding="utf-8",
    )
    with pytest.raises(ProjectConfigError):
        load_project_config(config_path)
