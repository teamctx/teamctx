from __future__ import annotations

import json
from pathlib import Path
from typing import Any, cast

from click.testing import CliRunner

from teamctx.cli import main
from teamctx.contract_documents import load_contract_document
from teamctx.contract_render import (
    render_contract_context,
    render_contract_open_source,
    render_contract_why,
)

ROOT = Path(__file__).resolve().parent.parent
CONTRACT_FIXTURE = (
    ROOT / "docs/product/discovery/fixtures/contracts/v0/core-contract-document.json"
)


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


def test_cli_context_requires_one_input() -> None:
    runner = CliRunner()

    result = runner.invoke(main, ["context"])

    assert result.exit_code != 0
    assert "Provide --fixture or --contract" in result.output


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
