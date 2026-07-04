from __future__ import annotations

import json
from pathlib import Path

import pytest

from teamctx.project_config import (
    ProjectConfigError,
    build_work_start_project_config,
    load_project_config,
    write_project_config,
)


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
    assert config.work_start.forge == "github"
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


def test_project_config_loads_forge_jira_and_confluence_blocks(tmp_path: Path) -> None:
    config_path = tmp_path / "config.json"
    config_path.write_text(
        json.dumps(
            {
                "schema_version": "teamctx.project_config.v0",
                "work_start": {
                    "repo": "acme/widgets",
                    "forge": "gitlab",
                    "jira": {"base_url": "https://example.atlassian.net/"},
                    "confluence": {
                        "base_url": "https://example.atlassian.net/wiki/",
                        "space_key": "DEV",
                    },
                },
            }
        ),
        encoding="utf-8",
    )

    config = load_project_config(config_path)

    assert config.work_start is not None
    assert config.work_start.forge == "gitlab"
    assert config.work_start.jira is not None
    assert config.work_start.jira.base_url == "https://example.atlassian.net"
    assert config.work_start.confluence is not None
    assert config.work_start.confluence.base_url == "https://example.atlassian.net"
    assert config.work_start.confluence.space_key == "DEV"


def test_project_config_allows_confluence_without_jira(tmp_path: Path) -> None:
    config_path = tmp_path / "config.json"
    config_path.write_text(
        json.dumps(
            {
                "schema_version": "teamctx.project_config.v0",
                "work_start": {
                    "repo": "acme/widgets",
                    "confluence": {
                        "base_url": "https://example.atlassian.net/wiki",
                        "space_key": "DEV",
                    },
                },
            }
        ),
        encoding="utf-8",
    )

    config = load_project_config(config_path)

    assert config.work_start is not None
    assert config.work_start.jira is None
    assert config.work_start.confluence is not None
    assert config.work_start.confluence.base_url == "https://example.atlassian.net"
    assert config.work_start.confluence.space_key == "DEV"


def test_build_work_start_project_config_includes_forge() -> None:
    config = build_work_start_project_config(
        repo="group/sub/project",
        forge="gitlab",
        docs_root="docs",
    )

    assert config.work_start is not None
    assert config.work_start.repo == "group/sub/project"
    assert config.work_start.forge == "gitlab"
    assert config.work_start.docs_root == "docs"


def test_work_start_project_config_round_trips_forge(tmp_path: Path) -> None:
    config_path = tmp_path / "config.json"
    config = build_work_start_project_config(
        repo="group/sub/project",
        forge="gitlab",
        docs_root="docs",
    )

    write_project_config(config_path, config, exclude_defaults=True)
    loaded = load_project_config(config_path)

    assert loaded == config
    body = json.loads(config_path.read_text(encoding="utf-8"))
    assert body["work_start"]["forge"] == "gitlab"


def test_project_config_rejects_unknown_jira_fields(tmp_path: Path) -> None:
    config_path = tmp_path / "config.json"
    config_path.write_text(
        json.dumps(
            {
                "schema_version": "teamctx.project_config.v0",
                "work_start": {
                    "repo": "acme/widgets",
                    "jira": {"base_url": "https://example.atlassian.net", "surprise": True},
                },
            }
        ),
        encoding="utf-8",
    )

    with pytest.raises(ProjectConfigError):
        load_project_config(config_path)
