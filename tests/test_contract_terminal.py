from __future__ import annotations

import json
from pathlib import Path
from typing import Any, cast

from click.testing import CliRunner
from pytest import MonkeyPatch

from teamctx.cli import main
from teamctx.contract_documents import load_contract_document
from teamctx.contract_render import (
    render_contract_context,
    render_contract_open_source,
    render_contract_why,
)

ROOT = Path(__file__).resolve().parent.parent
CONTRACT_FIXTURE = ROOT / "docs/product/discovery/fixtures/contracts/v0/core-contract-document.json"


def write_local_contract(path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(CONTRACT_FIXTURE.read_text(encoding="utf-8"), encoding="utf-8")


def test_contract_context_renders_terminal_working_context() -> None:
    document = load_contract_document(CONTRACT_FIXTURE)

    output = render_contract_context(document)

    assert output.startswith("Working context\n")
    assert "Needs attention" in output
    assert "Another open PR changed src/auth/token.py 11 minutes ago." in output
    assert "Project guidance" in output
    assert "Token rotation must preserve compatibility" in output


def test_contract_why_explains_card_without_source_text() -> None:
    document = load_contract_document(CONTRACT_FIXTURE)

    output = render_contract_why(document, "card_pr_collision")

    assert output.startswith("Show why\n")
    assert "same repository and file path" in output
    assert "Source: GitHub PR #482" in output
    assert "Source body: available only by explicit source-open action" in output


def test_cli_context_accepts_contract_document() -> None:
    runner = CliRunner()

    result = runner.invoke(main, ["context", "--contract", str(CONTRACT_FIXTURE)])

    assert result.exit_code == 0
    assert "Working context" in result.output
    assert "Another open PR changed src/auth/token.py 11 minutes ago." in result.output


def test_cli_why_accepts_contract_document() -> None:
    runner = CliRunner()

    result = runner.invoke(main, ["why", "card_pr_collision", "--contract", str(CONTRACT_FIXTURE)])

    assert result.exit_code == 0
    assert "Show why" in result.output
    assert "Confidence: high" in result.output


def test_contract_open_source_keeps_status_only_body_closed() -> None:
    document = load_contract_document(CONTRACT_FIXTURE)

    output = render_contract_open_source(document, "card_stale_docs")

    assert output.startswith("Open source\n")
    assert "Confluence Release Checklist" in output
    assert "Source body unavailable." in output
    assert "allowed metadata" in output


def test_cli_open_source_accepts_contract_document() -> None:
    runner = CliRunner()

    result = runner.invoke(
        main, ["open-source", "card_stale_docs", "--contract", str(CONTRACT_FIXTURE)]
    )

    assert result.exit_code == 0
    assert "Source body unavailable." in result.output


def test_cli_context_defaults_to_local_contract(tmp_path: Path, monkeypatch: MonkeyPatch) -> None:
    runner = CliRunner()
    write_local_contract(tmp_path / ".teamctx/context.json")
    monkeypatch.chdir(tmp_path)

    result = runner.invoke(main, ["context"])

    assert result.exit_code == 0
    assert "Working context" in result.output
    assert "Another open PR changed src/auth/token.py 11 minutes ago." in result.output


def test_cli_why_and_open_source_use_configured_local_contract(
    tmp_path: Path, monkeypatch: MonkeyPatch
) -> None:
    runner = CliRunner()
    context_path = tmp_path / "cache/context.json"
    config_path = tmp_path / ".teamctx/config.json"
    write_local_contract(context_path)
    config_path.parent.mkdir(parents=True, exist_ok=True)
    config_path.write_text(
        json.dumps(
            {
                "schema_version": "teamctx.project_config.v0",
                "default_output": str(context_path),
            }
        ),
        encoding="utf-8",
    )
    monkeypatch.chdir(tmp_path)

    why = runner.invoke(main, ["why", "card_pr_collision"])
    opened = runner.invoke(main, ["open-source", "card_stale_docs"])

    assert why.exit_code == 0
    assert "same repository and file path" in why.output
    assert opened.exit_code == 0
    assert "Source body unavailable." in opened.output


def test_cli_context_without_local_cache_explains_refresh_next_step(
    tmp_path: Path, monkeypatch: MonkeyPatch
) -> None:
    runner = CliRunner()
    monkeypatch.chdir(tmp_path)

    result = runner.invoke(main, ["context"])

    assert result.exit_code != 0
    assert "No local TeamCtx context" in result.output
    assert "teamctx refresh" in result.output


def test_cli_refresh_writes_contract_document_and_context_reads_it(tmp_path: Path) -> None:
    runner = CliRunner()
    output_path = tmp_path / "context.json"

    refresh = runner.invoke(
        main,
        [
            "refresh",
            "--github-repo",
            "org/app",
            "--path",
            "src/auth/token.py",
            "--task",
            "Update token rotation",
            "--output",
            str(output_path),
        ],
        env={"GITHUB_TOKEN": ""},
    )

    assert refresh.exit_code == 0
    assert output_path.exists()
    data = cast(dict[str, Any], json.loads(output_path.read_text(encoding="utf-8")))
    assert data["source_statuses"][0]["status"] == "unavailable"

    context = runner.invoke(main, ["context", "--contract", str(output_path)])

    assert context.exit_code == 0
    assert "No working context for this task." in context.output
    assert "Source status" in context.output
    assert "GitHub PR metadata is unavailable because no token is configured." in context.output
