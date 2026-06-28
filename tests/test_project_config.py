from __future__ import annotations

import json
from pathlib import Path
from typing import Any, cast

import pytest
from click.testing import CliRunner

from teamctx.cli import main
from teamctx.project_config import ProjectConfigError, load_project_config


def write_config(path: Path, *, output_path: Path) -> None:
    path.write_text(
        json.dumps(
            {
                "schema_version": "teamctx.project_config.v0",
                "github": {
                    "repo": "org/app",
                    "token_env": "TEAMCTX_TEST_GITHUB_TOKEN",
                    "include_title": False,
                },
                "default_output": str(output_path),
            }
        ),
        encoding="utf-8",
    )


def test_project_config_loads_github_defaults(tmp_path: Path) -> None:
    config_path = tmp_path / "config.json"
    output_path = tmp_path / "context.json"
    write_config(config_path, output_path=output_path)

    config = load_project_config(config_path)

    assert config.github is not None
    assert config.github.repo == "org/app"
    assert config.github.token_env == "TEAMCTX_TEST_GITHUB_TOKEN"
    assert config.default_output == str(output_path)


def test_project_config_rejects_unknown_fields(tmp_path: Path) -> None:
    config_path = tmp_path / "config.json"
    config_path.write_text(
        json.dumps(
            {
                "schema_version": "teamctx.project_config.v0",
                "github": {"repo": "org/app"},
                "mine_everything": True,
            }
        ),
        encoding="utf-8",
    )

    with pytest.raises(ProjectConfigError):
        load_project_config(config_path)



def test_refresh_uses_project_config_defaults(tmp_path: Path) -> None:
    runner = CliRunner()
    config_path = tmp_path / "config.json"
    output_path = tmp_path / "context.json"
    write_config(config_path, output_path=output_path)

    result = runner.invoke(
        main,
        [
            "refresh",
            "--config",
            str(config_path),
            "--path",
            "src/auth/token.py",
            "--task",
            "Update token rotation",
        ],
        env={"TEAMCTX_TEST_GITHUB_TOKEN": ""},
    )

    assert result.exit_code == 0
    assert output_path.exists()
    data = cast(dict[str, Any], json.loads(output_path.read_text(encoding="utf-8")))
    assert data["request_context"]["repo"] == "org/app"
    assert data["source_statuses"][0]["scope"]["repo"] == "org/app"


def test_refresh_requires_repo_when_config_missing(tmp_path: Path) -> None:
    runner = CliRunner()

    result = runner.invoke(
        main,
        [
            "refresh",
            "--config",
            str(tmp_path / "missing.json"),
            "--path",
            "src/auth/token.py",
        ],
        env={"GITHUB_TOKEN": ""},
    )

    assert result.exit_code != 0
    assert "Provide --github-repo or configure github.repo" in result.output


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
        json.dumps(
            {"schema_version": "teamctx.project_config.v0", "github": {"repo": "org/app"}}
        ),
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
