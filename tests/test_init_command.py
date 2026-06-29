"""Tests for the `teamctx init` command (work-start scaffold).

init scaffolds .teamctx/config.json with a work_start section, auto-detects the
repo from the git origin remote, and auto-detects docs_root from the presence of a
docs/ directory.  All git I/O is monkeypatched; no network, no subprocess.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any, cast

from click.testing import CliRunner

from teamctx.cli import main
from teamctx.project_config import DEFAULT_CONFIG_PATH

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _config_at(tmp_path: Path) -> dict[str, Any]:
    return cast(
        dict[str, Any],
        json.loads((tmp_path / DEFAULT_CONFIG_PATH).read_text(encoding="utf-8")),
    )


# ---------------------------------------------------------------------------
# Case 1: auto-detect repo, no docs/ -> writes a clean work_start-only config,
#         exits 0, prints a runnable next command and token guidance.
# ---------------------------------------------------------------------------


def test_init_auto_detects_repo_writes_work_start_config(
    monkeypatch: Any, tmp_path: Path
) -> None:
    monkeypatch.chdir(tmp_path)
    monkeypatch.setattr("teamctx.cli.detect_repo", lambda root: "acme/widgets")

    result = CliRunner().invoke(main, ["init"], catch_exceptions=False)

    assert result.exit_code == 0, result.output
    data = _config_at(tmp_path)
    # The canonical first-run file is exactly {schema_version, work_start}: no
    # legacy github:null or default_output cruft from model defaults.
    assert set(data) == {"schema_version", "work_start"}
    # docs_root unset => omitted entirely; only repo present.
    assert data["work_start"] == {"repo": "acme/widgets"}
    # The printed next command is runnable as-is (work-start requires --path).
    assert (
        "teamctx work-start --path <file you are about to edit>" in result.output
    )
    assert "GITHUB_TOKEN" in result.output


# ---------------------------------------------------------------------------
# Case 2: --repo overrides detection
# ---------------------------------------------------------------------------


def test_init_repo_flag_overrides_auto_detection(
    monkeypatch: Any, tmp_path: Path
) -> None:
    monkeypatch.chdir(tmp_path)
    monkeypatch.setattr("teamctx.cli.detect_repo", lambda root: "auto/detected")

    result = CliRunner().invoke(
        main, ["init", "--repo", "owner/name"], catch_exceptions=False
    )

    assert result.exit_code == 0, result.output
    assert _config_at(tmp_path)["work_start"]["repo"] == "owner/name"


# ---------------------------------------------------------------------------
# Case 3a: docs_root auto-detect -> docs/ present => "docs"
# ---------------------------------------------------------------------------


def test_init_detects_docs_root_when_docs_dir_exists(
    monkeypatch: Any, tmp_path: Path
) -> None:
    monkeypatch.chdir(tmp_path)
    monkeypatch.setattr("teamctx.cli.detect_repo", lambda root: "acme/widgets")
    (tmp_path / "docs").mkdir()

    result = CliRunner().invoke(main, ["init"], catch_exceptions=False)

    assert result.exit_code == 0, result.output
    assert _config_at(tmp_path)["work_start"]["docs_root"] == "docs"
    # output tells the user docs root was found
    assert "docs" in result.output.lower()


# ---------------------------------------------------------------------------
# Case 3b: docs_root auto-detect -> no docs/ => None, output says not set
# ---------------------------------------------------------------------------


def test_init_docs_root_none_when_no_docs_dir_output_says_not_set(
    monkeypatch: Any, tmp_path: Path
) -> None:
    monkeypatch.chdir(tmp_path)
    monkeypatch.setattr("teamctx.cli.detect_repo", lambda root: "acme/widgets")

    result = CliRunner().invoke(main, ["init"], catch_exceptions=False)

    assert result.exit_code == 0, result.output
    ws = _config_at(tmp_path)["work_start"]
    assert ws.get("docs_root") is None
    assert "not set" in result.output


# ---------------------------------------------------------------------------
# Case 4: --docs-root overrides detection
# ---------------------------------------------------------------------------


def test_init_docs_root_flag_overrides_detection(
    monkeypatch: Any, tmp_path: Path
) -> None:
    monkeypatch.chdir(tmp_path)
    monkeypatch.setattr("teamctx.cli.detect_repo", lambda root: "acme/widgets")

    result = CliRunner().invoke(
        main, ["init", "--docs-root", "design/docs"], catch_exceptions=False
    )

    assert result.exit_code == 0, result.output
    assert _config_at(tmp_path)["work_start"]["docs_root"] == "design/docs"


def test_init_rejects_non_github_repo(monkeypatch: Any, tmp_path: Path) -> None:
    monkeypatch.chdir(tmp_path)
    result = CliRunner().invoke(main, ["init", "--repo", "git@gitlab.com:o/n.git"])
    assert result.exit_code != 0
    assert "GitHub" in result.output


# ---------------------------------------------------------------------------
# Case 5a: existing config + no --force -> non-zero, hints --force, file unchanged
# ---------------------------------------------------------------------------


def test_init_refuses_to_overwrite_without_force(
    monkeypatch: Any, tmp_path: Path
) -> None:
    monkeypatch.chdir(tmp_path)
    monkeypatch.setattr("teamctx.cli.detect_repo", lambda root: "acme/widgets")

    CliRunner().invoke(main, ["init"], catch_exceptions=False)
    original = (tmp_path / DEFAULT_CONFIG_PATH).read_text(encoding="utf-8")

    result = CliRunner().invoke(main, ["init"])

    assert result.exit_code != 0
    assert "--force" in result.output
    assert (tmp_path / DEFAULT_CONFIG_PATH).read_text(encoding="utf-8") == original


# ---------------------------------------------------------------------------
# Case 5b: existing config + --force -> overwrites
# ---------------------------------------------------------------------------


def test_init_overwrites_existing_config_with_force(
    monkeypatch: Any, tmp_path: Path
) -> None:
    monkeypatch.chdir(tmp_path)
    monkeypatch.setattr("teamctx.cli.detect_repo", lambda root: "acme/widgets")

    CliRunner().invoke(main, ["init"], catch_exceptions=False)

    result = CliRunner().invoke(
        main, ["init", "--repo", "new/repo", "--force"], catch_exceptions=False
    )

    assert result.exit_code == 0, result.output
    assert _config_at(tmp_path)["work_start"]["repo"] == "new/repo"


# ---------------------------------------------------------------------------
# Case 6: no detectable repo and no --repo -> non-zero with guidance
# ---------------------------------------------------------------------------


def test_init_errors_with_guidance_when_repo_not_detectable(
    monkeypatch: Any, tmp_path: Path
) -> None:
    monkeypatch.chdir(tmp_path)
    monkeypatch.setattr("teamctx.cli.detect_repo", lambda root: None)

    result = CliRunner().invoke(main, ["init"])

    assert result.exit_code != 0
    assert "--repo" in result.output
