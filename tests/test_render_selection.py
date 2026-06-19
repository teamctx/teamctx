"""Human-plane render of the broker's answer: derived cards + honest coverage.

The renderer is deterministic (never via an LLM) and prints, never blocks. Its load-
bearing job beyond listing cards is the Coverage block: when coverage is incomplete it
must say, in plain words, that absence of a card is not an all-clear.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any, cast

from teamctx.contract_render import render_selection
from teamctx.core.contracts import CoreContractDocument
from teamctx.core.select import select_context

ROOT = Path(__file__).resolve().parent.parent
CONTRACT_FIXTURE = (
    ROOT / "docs/product/discovery/fixtures/contracts/v0/core-contract-document.json"
)


def load_document() -> CoreContractDocument:
    data = cast("dict[str, Any]", json.loads(CONTRACT_FIXTURE.read_text(encoding="utf-8")))
    return CoreContractDocument.model_validate(data)


def test_render_shows_complete_coverage_when_mandated_source_is_fresh() -> None:
    document = load_document()
    git_hosting_fresh = document.source_statuses[0].model_copy(
        update={
            "source_id": "github_pr_metadata",
            "source_family": "git_hosting",
            "status": "fresh",
        }
    )
    selection = select_context(
        document.request_context, document.source_signals, [git_hosting_fresh]
    )

    text = render_selection(selection)

    # git_hosting fresh -> the collision query's closure is complete -> the complete line.
    assert "Coverage complete across checked sources." in text


def test_render_shows_collision_card_and_honest_incomplete_coverage() -> None:
    document = load_document()
    selection = select_context(
        document.request_context, document.source_signals, document.source_statuses
    )

    text = render_selection(selection)

    assert "Needs attention" in text
    assert "src/auth/token.py" in text  # the derived collision card content
    assert "GitHub PR #482" in text  # source-backed display
    assert "Coverage" in text
    # absence is not clearance: incomplete coverage must say so in plain words.
    assert "not an all-clear" in text
