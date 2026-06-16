from __future__ import annotations

import json
from pathlib import Path
from typing import Any, cast

import pytest
from pydantic import ValidationError

from teamctx.core.contracts import CoreContractDocument, load_core_contract_document

ROOT = Path(__file__).resolve().parent.parent
CONTRACT_FIXTURE = (
    ROOT / "docs/product/discovery/fixtures/contracts/v0/core-contract-document.json"
)
CORE_DIR = ROOT / "src/teamctx/core"
JsonObject = dict[str, Any]


def load_contract_fixture() -> JsonObject:
    return cast(JsonObject, json.loads(CONTRACT_FIXTURE.read_text(encoding="utf-8")))


def object_list(data: JsonObject, key: str) -> list[JsonObject]:
    return cast(list[JsonObject], data[key])


def test_core_contract_fixture_round_trips_deterministically() -> None:
    data = load_contract_fixture()

    document = load_core_contract_document(data)

    assert document.model_dump(mode="json") == data
    assert CoreContractDocument.model_validate(document.model_dump(mode="json")) == document


def test_context_cards_carry_explainability_fields() -> None:
    document = load_core_contract_document(load_contract_fixture())

    for card in document.context_cards:
        assert card.source_display
        assert card.reason
        assert card.scope
        assert card.freshness in {"fresh", "stale", "unavailable", "blocked", "disabled", "retired"}
        assert card.confidence in {"high", "medium", "low"}
        assert card.source_body in {
            "openable",
            "status_only",
            "blocked",
            "unavailable",
            "not_collected",
        }


def test_unknown_fields_cannot_bypass_policy() -> None:
    data = load_contract_fixture()
    signal = object_list(data, "source_signals")[0]
    policy = cast(JsonObject, signal["policy"])
    policy["can_render_private_messages"] = True

    with pytest.raises(ValidationError):
        load_core_contract_document(data)


def test_hidden_signals_cannot_be_agent_visible() -> None:
    data = load_contract_fixture()
    signal = object_list(data, "source_signals")[0]
    signal["visibility"] = "hidden"

    with pytest.raises(ValidationError, match="hidden source signals"):
        load_core_contract_document(data)


def test_blocked_source_open_target_cannot_include_source_text() -> None:
    data = load_contract_fixture()
    target = object_list(data, "source_open_targets")[0]
    target["body_availability"] = "blocked"

    with pytest.raises(ValidationError, match="only available source bodies"):
        load_core_contract_document(data)


def test_active_guidance_requires_review_metadata() -> None:
    data = load_contract_fixture()
    guidance = object_list(data, "guidance_records")[0]
    guidance["review"] = None

    with pytest.raises(ValidationError, match="active guidance requires review"):
        load_core_contract_document(data)


def test_draft_guidance_cannot_render_to_agent() -> None:
    data = load_contract_fixture()
    guidance = object_list(data, "guidance_records")[0]
    guidance["status"] = "draft"

    with pytest.raises(ValidationError, match="draft or retired guidance"):
        load_core_contract_document(data)


def test_project_guidance_cards_must_reference_guidance_records() -> None:
    data = load_contract_fixture()
    card = object_list(data, "context_cards")[1]
    card["refs"] = ["sig_pr_482_collision"]

    with pytest.raises(ValidationError, match="project guidance cards"):
        load_core_contract_document(data)


def test_core_package_has_no_file_or_runtime_side_effect_imports() -> None:
    banned_imports = (
        "from pathlib",
        "import pathlib",
        "import os",
        "import subprocess",
        "import tempfile",
        "import time",
        "from datetime",
        "import datetime",
        "import random",
        "import secrets",
    )

    for path in CORE_DIR.glob("*.py"):
        text = path.read_text(encoding="utf-8")
        for banned in banned_imports:
            assert banned not in text, f"{path.relative_to(ROOT)} imports {banned}"
