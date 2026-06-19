"""Verifiable replay (Theorem 1): the snapshot digest binds the exact inputs."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any, cast

from teamctx.core.contracts import CoreContractDocument
from teamctx.core.snapshot import snapshot_digest

ROOT = Path(__file__).resolve().parent.parent
FIXTURE = ROOT / "docs/product/discovery/fixtures/contracts/v0/core-contract-document.json"


def _document() -> CoreContractDocument:
    data = cast("dict[str, Any]", json.loads(FIXTURE.read_text(encoding="utf-8")))
    return CoreContractDocument.model_validate(data)


def test_digest_is_stable_for_identical_inputs() -> None:
    doc = _document()
    a = snapshot_digest(doc.request_context, doc.source_signals, doc.source_statuses, [])
    b = snapshot_digest(doc.request_context, doc.source_signals, doc.source_statuses, [])
    assert a == b
    assert len(a) == 64  # sha256 hex


def test_digest_changes_when_an_input_changes() -> None:
    doc = _document()
    base = snapshot_digest(doc.request_context, doc.source_signals, doc.source_statuses, [])
    other_request = doc.request_context.model_copy(update={"paths": ["src/changed.py"]})
    changed = snapshot_digest(other_request, doc.source_signals, doc.source_statuses, [])
    assert base != changed


def test_digest_is_order_independent_for_signals() -> None:
    doc = _document()
    a = snapshot_digest(doc.request_context, doc.source_signals, doc.source_statuses, [])
    b = snapshot_digest(
        doc.request_context, list(reversed(doc.source_signals)), doc.source_statuses, []
    )
    assert a == b
